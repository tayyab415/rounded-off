"""Judge harness: batched LLM labelling with quality controls built in (design and sources: notes/JUDGE_HARNESS.md).

  python3 -I scripts/judge_harness.py RUBRIC OUT_DIR IN1.jsonl [IN2.jsonl ...] [options]
    --judge MODEL        primary judge (default DeepSeek-V4.1-Flash); --jury MODEL second judge (default GLM-5.3-Flash)
    --batch-min 12 --batch-max 18   items per call (group sizes drawn in this range)
    --anchors 2          hand-labelled items hidden in each batch (rubrics that have them)
    --perm-frac 0.15     share of items re-judged in a new grouping; disagreements get a third vote
    --jury-frac 0.15     share of items also judged by the jury model; Cohen's kappa reported
    --limit N            first N applicable items per file (smoke test)
Steps: filter rows the rubric applies to; refuse harmful sets (they stay on our GPU); route each row away from a judge
of its own family; reuse cached labels; shuffle; group; hide anchors; label; re-judge batches that miss an anchor;
permutation check with majority vote; jury sample; write labelled files and a summary JSON.
"""
import argparse, collections, hashlib, json, math, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nebius_batch as nb
from judge_rubrics import RUBRICS

DS, GLM = "deepseek-ai/DeepSeek-V4.1-Flash-1017", "zai-org/GLM-5.3-Flash"
FAMILY = {DS: "deepseek", GLM: "glm", "deepseek-ai/DeepSeek-V4-Pro-0813": "deepseek"}
AUTHOR_FAMILY = {"DSV4F": "deepseek", "DSV4P": "deepseek", "GLM53F": "glm"}     # agent tag -> family
HARMFUL_SETS = {"harmbench", "xstest_unsafe", "bank_redteam"}                   # never sent to an outside API
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def parse(text, n, valid):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    out, rx = {}, re.compile(rf"^(?:{valid})$")
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            for k, v in json.loads(m.group(0)).items():
                v = re.sub(r"[^A-Z]", "", str(v).upper())
                if str(k).strip().isdigit() and rx.match(v): out[int(k)] = v
        except json.JSONDecodeError:
            pass
    if not out:
        for k, v in re.findall(r"(\d+)\s*[:=)\-]\s*\"?([A-Z]+)", text.upper()):
            if rx.match(v): out[int(k)] = v
    return {k: v for k, v in out.items() if 1 <= k <= n}


def call(model, rub, items, tag):
    user = "\n\n".join(f"### Item {i + 1}\n{rub['render'](it)}" for i, it in enumerate(items))
    user += (f"\n\nGrade each of the {len(items)} items independently; they are unrelated. Reply with ONLY a JSON object "
             f"mapping item number to its grade, for example {{\"1\": \"...\", \"2\": \"...\"}}.")
    width = 4 if "{4}" in rub["valid"] else 1
    got = parse(nb._post(model, [{"role": "system", "content": rub["system"]}, {"role": "user", "content": user}],
                         max_tokens=(8 + width) * len(items) + 40, tag=tag), len(items), rub["valid"])
    for i, it in enumerate(items):          # anything missing: ask alone
        if i + 1 not in got:
            one = parse(nb._post(model, [{"role": "system", "content": rub["system"]},
                                         {"role": "user", "content": f"### Item 1\n{rub['render'](it)}\n\nReply with ONLY {{\"1\": \"<grade>\"}}."}],
                                 max_tokens=24, tag=tag + "-single"), 1, rub["valid"])
            if 1 in one: got[i + 1] = one[1]
    return [got.get(i + 1) for i in range(len(items))]


def groups(n, lo, hi, rnd):
    sizes, left = [], n
    while left > 0:
        s = min(left, rnd.randint(lo, hi))
        if 0 < left - s < lo and len(sizes) == 0: s = left
        sizes.append(s); left -= s
    return sizes


def kappa(pairs):
    if not pairs: return None
    agree = sum(a == b for a, b in pairs) / len(pairs)
    pa = sum(a for a, _ in pairs) / len(pairs); pb = sum(b for _, b in pairs) / len(pairs)
    pe = pa * pb + (1 - pa) * (1 - pb)
    return round((agree - pe) / (1 - pe), 3) if pe < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rubric", choices=sorted(RUBRICS)); ap.add_argument("out_dir"); ap.add_argument("files", nargs="+")
    ap.add_argument("--judge", default=DS); ap.add_argument("--jury", default=GLM)
    ap.add_argument("--batch-min", type=int, default=12); ap.add_argument("--batch-max", type=int, default=18)
    ap.add_argument("--anchors", type=int, default=2); ap.add_argument("--perm-frac", type=float, default=0.15)
    ap.add_argument("--jury-frac", type=float, default=0.15); ap.add_argument("--limit", type=int); ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    rub, rnd = RUBRICS[a.rubric], random.Random(a.seed)
    os.makedirs(a.out_dir, exist_ok=True)
    cache_path = os.path.join(ROOT, "results", "raw", "judge_cache", f"{a.rubric}.jsonl")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    cache = {}
    if os.path.exists(cache_path):
        for l in open(cache_path): c = json.loads(l); cache[c["key"]] = c["label"]
    sysh = hashlib.sha256(rub["system"].encode()).hexdigest()[:8]           # editing a rubric invalidates its cache
    key = lambda model, r: hashlib.sha256(f"{a.rubric}|{sysh}|{model}|{rub['render'](r)}".encode()).hexdigest()[:24]

    files = {f: [json.loads(l) for l in open(f, encoding="utf-8")] for f in a.files}
    todo = []                                    # (file, row index, row, judge)
    for f, rows in files.items():
        app = [i for i, r in enumerate(rows) if rub["applies"](r)]
        if a.limit: app = app[:a.limit]
        for i in app:
            r = rows[i]
            if r.get("set") in HARMFUL_SETS: sys.exit(f"refusing: {f} row {i} is from {r['set']} (harmful content stays local)")
            fam = AUTHOR_FAMILY.get(str(r.get("model", "")).split(".")[0])
            judge = a.judge if FAMILY.get(a.judge) != fam else a.jury
            todo.append((f, i, r, judge))
    anchors = []
    if rub["anchors"] and a.anchors:
        path, fld = rub["anchors"]; anchors = [x for x in json.load(open(os.path.join(ROOT, path))) if x.get(fld)]
        for x in anchors: x["_gold"] = x[fld]

    labels, first = {}, {}
    pending = [(t, j) for t, j in ((t, t[3]) for t in todo) if key(j, t[2]) not in cache]
    for t in todo:
        k = key(t[3], t[2])
        if k in cache: labels[(t[0], t[1])] = cache[k]
    anchor_log = []

    def run_group(model, items, tag, use_anchors=True):
        mix = list(items); gold = []
        if use_anchors and anchors:
            for g in rnd.sample(anchors, min(a.anchors, len(anchors))):
                pos = rnd.randint(0, len(mix)); mix.insert(pos, ("anchor", g)); gold.append(g)
        rows = [x[1] if isinstance(x, tuple) and x[0] == "anchor" else x[2] for x in mix]
        out = call(model, rub, rows, tag)
        res, ok = [], []
        for x, lab in zip(mix, out):
            if isinstance(x, tuple) and x[0] == "anchor": ok.append(rub["binary"](lab) == rub["binary"](x[1]["_gold"]) if lab else False)
            else: res.append((x, lab))
        return res, ok

    by_judge = collections.defaultdict(list)
    for t, j in pending: by_judge[j].append(t)
    for j, items in by_judge.items():
        rnd.shuffle(items)
        sizes = groups(len(items), a.batch_min, a.batch_max, rnd); chunks, pos = [], 0
        for s in sizes: chunks.append(items[pos:pos + s]); pos += s
        if not chunks: continue
        results = [run_group(j, chunks[0], f"{a.rubric}")]          # warm the cache first
        with ThreadPoolExecutor(6) as ex: results += list(ex.map(lambda c: run_group(j, c, a.rubric), chunks[1:]))
        for chunk, (res, ok) in zip(chunks, results):
            anchor_log += ok
            if ok and not all(ok):                                   # missed an anchor: re-judge this batch in a new order
                again, _ = run_group(j, rnd.sample(chunk, len(chunk)), a.rubric + "-redo", use_anchors=False)
                prev = {id(x): lab for x, lab in res}
                res = [(x, lab if lab == prev.get(id(x)) else None) for x, lab in again]
                for x, lab in res:
                    if lab is None:                                   # the two passes disagree: third vote decides
                        third = call(j, rub, [x[2]], a.rubric + "-vote")[0]
                        votes = collections.Counter([prev.get(id(x)), [l for y, l in again if y is x][0], third])
                        lab = votes.most_common(1)[0][0]
                    labels[(x[0], x[1])] = lab
            else:
                for x, lab in res: labels[(x[0], x[1])] = lab
            first.update({(x[0], x[1]): lab for x, lab in res})

    # permutation check: re-judge a sample in a new grouping; disagreements get a third vote
    perm_pairs = []
    sample = [t for t in rnd.sample(todo, int(len(todo) * a.perm_frac)) if (t[0], t[1]) in first]
    if sample:
        rnd.shuffle(sample); sample.sort(key=lambda t: t[3]); out = []      # new grouping, one judge per call
        for jm in sorted({t[3] for t in sample}):
            part = [t for t in sample if t[3] == jm]
            for s in range(0, len(part), a.batch_max): out += call(jm, rub, [t[2] for t in part[s:s + a.batch_max]], a.rubric + "-perm")
        for t, lab2 in zip(sample, out):
            lab1 = labels[(t[0], t[1])]; perm_pairs.append((lab1, lab2))
            if lab2 and lab1 != lab2:
                third = call(t[3], rub, [t[2]], a.rubric + "-vote")[0]
                labels[(t[0], t[1])] = collections.Counter([lab1, lab2, third]).most_common(1)[0][0]

    # jury: a sample also judged by the other family's model
    jury_pairs, jury_labels = [], {}
    js = rnd.sample(todo, int(len(todo) * a.jury_frac))
    for jm in {a.judge, a.jury}:
        part = [t for t in js if t[3] != jm]
        for s in range(0, len(part), a.batch_max):
            chunk = part[s:s + a.batch_max]
            for t, lab in zip(chunk, call(jm, rub, [t[2] for t in chunk], a.rubric + "-jury")):
                jury_labels[(t[0], t[1])] = (jm, lab)
                if lab and labels.get((t[0], t[1])): jury_pairs.append((rub["binary"](labels[(t[0], t[1])]), rub["binary"](lab)))

    with open(cache_path, "a") as cf:
        for t in todo:
            k = key(t[3], t[2])
            if k not in cache and labels.get((t[0], t[1])): cf.write(json.dumps({"key": k, "label": labels[(t[0], t[1])]}) + "\n")
    dist = collections.Counter()
    for f, rows in files.items():
        with open(os.path.join(a.out_dir, os.path.basename(f)), "w", encoding="utf-8") as g:
            for i, r in enumerate(rows):
                if (f, i) in labels:
                    lab = labels[(f, i)]; dist[lab] += 1
                    r[rub["field"] + "_prev"] = r.get(rub["field"])
                    r[rub["field"]] = rub["labels"].get(lab) if rub["labels"] and lab else lab
                    r[rub["field"] + "_judge"] = next(t[3] for t in todo if t[0] == f and t[1] == i)
                    r[rub["field"] + "_rubric"] = a.rubric
                    if (f, i) in jury_labels: r[rub["field"] + "_jury"] = jury_labels[(f, i)]
                g.write(json.dumps(r, ensure_ascii=False) + "\n")
    summ = {"rubric": a.rubric, "items": len(todo), "from_cache": len(todo) - len(pending), "labels": dict(dist),
            "unlabelled": sum(1 for t in todo if not labels.get((t[0], t[1]))),
            "anchor_accuracy": round(sum(anchor_log) / len(anchor_log), 3) if anchor_log else None, "anchors_seen": len(anchor_log),
            "permutation_consistency": round(sum(x == y for x, y in perm_pairs) / len(perm_pairs), 3) if perm_pairs else None,
            "permutation_n": len(perm_pairs),
            "permutation_consistency_binary": round(sum(rub["binary"](x) == rub["binary"](y) for x, y in perm_pairs if x and y) / max(1, sum(1 for x, y in perm_pairs if x and y)), 3) if perm_pairs else None,
            "permutation_flips": [f"{x}->{y}" for x, y in perm_pairs if x != y], "jury_kappa_binary": kappa(jury_pairs), "jury_n": len(jury_pairs),
            "jury_agreement_binary": round(sum(x == y for x, y in jury_pairs) / len(jury_pairs), 3) if jury_pairs else None,
            "cost": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in nb.STATS.items()}}
    json.dump(summ, open(os.path.join(a.out_dir, f"_summary_{a.rubric}.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
