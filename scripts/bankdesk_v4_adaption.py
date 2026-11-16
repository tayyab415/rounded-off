"""BankDesk v4, held-out TEST wording written by Adaption (a different generator from the GLM/DeepSeek writers of
train, rl and dev), so the headline does not only measure how well the agent copes with our own writers' style.

Same task as bankdesk_v4_words.py: the writer sees the structure, a style seed, the code-chosen facts and the
code-made reference code, never the hidden story (W.writer_task guarantees that). Each Adaption row's prompt is
W.WRITER_SYSTEM + the world's writer task; Adaption's adaptation pipeline writes the completion (prompt rephrase,
dedup and reasoning traces off). Returned rows are linked back to their world by the exact task text, then go
through the same code checks (W.code_checks), the same round-trip review (W.review, DeepSeek-V4.1-Flash on Nebius,
batched, through nebius_client.chat) and the same duplicate-answer limit (W.dup_check) as every other split.
Kept rows -> data/bankdesk_v4/words_test.jsonl, drops with reasons -> words_test.rejected.jsonl.
RULE V4-4 leak audit on the kept rows: python3 scripts/bankdesk_v4_words.py audit --name test [--regime shift]

  python3 scripts/bankdesk_v4_adaption.py tasks --prefix test --n 300 --attempts 2 --out data/adaption/bankdesk_v4_test/tasks_main.jsonl
  python3 scripts/bankdesk_v4_adaption.py launch --file .../tasks_main.jsonl --name v4-test-main [--dataset ID] [--go]   # estimate unless --go
  python3 scripts/bankdesk_v4_adaption.py fetch --dataset ID --out data/adaption/bankdesk_v4_test/out_main.jsonl
  python3 scripts/bankdesk_v4_adaption.py collect --out-files data/adaption/bankdesk_v4_test/out_main.jsonl --name test
  python3 scripts/bankdesk_v4_adaption.py topup --name test --prefix test --n 300 --k 2 --out .../tasks_topup1.jsonl
Shifted test (RULE V4-8): the same commands with --regime shift, --prefix shift and --name shift. The regime is set
before any world is sampled; task files carry world_hash, and collect refuses task files of another regime.
Rows: words_<name>.jsonl. Raw files and the job log: data/adaption/bankdesk_v4_<name>/.
Content: victim-side and genuine-customer messages only (allowed on Adaption and Nebius by AGENTS.md).
"""
import argparse, glob, json, os, re, sys, time
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk_v4 as g
import bankdesk_v4_env as e
import bankdesk_v4_words as W

WRITER = "adaption"
REVIEWER = W.DEEPSEEK
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def split_dir(name):
    """Task files, raw exports and the job log of one split (gitignored with the rest of data/adaption)."""
    return os.path.join(ROOT, "data", "adaption", f"bankdesk_v4_{name}")


ADA_DIR = split_dir("test")
TASK_HEADER = "\n\n=== TASK ===\n"
BLUEPRINT = ("You are a test-data writer. The prompt gives full instructions and one task. Follow them exactly. "
             "Reply with exactly one JSON object with the keys \"opening\" and \"answers\" as the prompt specifies: "
             "no markdown fences, no explanation, no text before or after the JSON.")


def task_text(world, lang, attempt=0):
    return W.WRITER_SYSTEM + TASK_HEADER + W.writer_task(world, e.case_facts(world), lang, attempt)


def task_rows(ids, attempt=0):
    out = []
    for wid in ids:
        w = g.sample_world(wid); lang = W.assign_lang(wid)
        out.append({"world_id": wid, "attempt": attempt, "lang": lang, "task": task_text(w, lang, attempt),
                    "regime": g.REGIME, "world_hash": g.params_hash()})
    return out


# ---------------------------------------------------------------- Adaption SDK
def client():
    from adaption import Adaption
    key = os.environ.get("ADAPTION_API_KEY", "")
    if not key:
        for l in open(os.path.expanduser("~/.config/adaption/env")):
            l = l.strip().removeprefix("export ").strip()
            if l.startswith("ADAPTION_API_KEY="): key = l.split("=", 1)[1].strip().strip("'\"")
    return Adaption(api_key=key)


def _dump(x):
    for attr in ("model_dump", "to_dict"):
        if hasattr(x, attr):
            try: return getattr(x, attr)()
            except Exception: pass
    return x if isinstance(x, (dict, list, str, int, float)) else repr(x)


def _status(c, did):
    st = c.datasets.get_status(did); d = _dump(st)
    return (d.get("status") if isinstance(d, dict) else getattr(st, "status", None)), d


def adapt_kwargs(key):
    return dict(column_mapping={"prompt": "task"}, training_type="instruction_dataset",
                recipe_specification={"recipes": {"prompt_rephrase": False, "deduplication": False, "reasoning_traces": False}},
                brand_controls={"blueprint": BLUEPRINT}, job_specification={"idempotency_key": key})


def launch(path, name, go=False, dataset=None, wait=900):
    c = client()
    if dataset is None:
        up = c.datasets.upload_file(path, name=name); d = _dump(up)
        dataset = d.get("dataset_id") or d.get("id") if isinstance(d, dict) else getattr(up, "dataset_id", None)
        print("uploaded:", json.dumps(d, default=str)[:600], flush=True)
        t0 = time.time()
        while time.time() - t0 < wait:          # wait for ingestion before adapting
            s, sd = _status(c, dataset)
            print(f"  {time.strftime('%H:%M:%S')} status {s}", flush=True)
            if s not in ("pending", "running", "uploading", "processing", None): break
            time.sleep(10)
    est = c.datasets.adapt(dataset, estimate=True, **adapt_kwargs(f"{name}-est"))
    print("estimate:", json.dumps(_dump(est), default=str)[:1500], flush=True)
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "name": name, "file": os.path.relpath(path, ROOT), "dataset_id": dataset,
           "rows": sum(1 for _ in open(path)), "estimate": _dump(est)}
    if go:
        run = c.datasets.adapt(dataset, **adapt_kwargs(f"{name}-run"))
        rec["launch"] = _dump(run); print("launched:", json.dumps(rec["launch"], default=str)[:1500], flush=True)
    with open(os.path.join(os.path.dirname(os.path.abspath(path)), "jobs.jsonl"), "a") as f: f.write(json.dumps(rec, default=str) + "\n")
    return dataset


def fetch(did, out, wait=7200):
    c = client(); t0 = time.time()
    while True:
        s, d = _status(c, did)
        prog = d.get("progress_percentage") if isinstance(d, dict) else None
        print(f"{time.strftime('%H:%M:%S')} {did[:8]} {s} {prog}", flush=True)
        if s in ("succeeded", "failed", "ready"): break
        if time.time() - t0 > wait: print("timeout; not downloaded"); return None
        time.sleep(30)
    c.datasets.download(did, file_format="jsonl").write_to_file(out)
    n = sum(1 for _ in open(out)); print(f"{s}: {n} rows -> {out}", flush=True)
    return n


# ---------------------------------------------------------------- linking returned rows to worlds
def task_index(d=ADA_DIR):
    """Every task text we ever sent -> (world_id, attempt, lang), from the task files in the split's folder.
    Refuses task files built under another regime than the current one (their worlds would differ)."""
    idx = {}
    for p in glob.glob(os.path.join(d, "tasks_*.jsonl")):
        for l in open(p):
            r = json.loads(l)
            if r.get("world_hash", g.params_hash()) != g.params_hash():
                raise SystemExit(f"{p}: tasks built under world_hash {r['world_hash']}, current regime {g.REGIME} is "
                                 f"{g.params_hash()}; pass the matching --regime")
            idx[r["task"].strip()] = (r["world_id"], r["attempt"], r["lang"])
    return idx


def _prompt_of(r):
    for k in ("original_prompt", "task", "prompt", "enhanced_prompt"):
        if isinstance(r.get(k), str) and r[k].strip(): return r[k]
    return ""


def _completion_of(r):
    for k in ("enhanced_completion", "completion", "original_completion"):
        if isinstance(r.get(k), str) and r[k].strip(): return r[k]
    return ""


def link(r, idx):
    """(world_id, attempt, lang, how) for one exported row. World id column first, then the exact task text,
    then the STYLE line + account number (unique per world and attempt)."""
    wid = r.get("world_id") or r.get("original_world_id")
    p = _prompt_of(r).strip()
    if p in idx:
        w, a, lang = idx[p]
        return w, a, lang, ("column" if wid == w else "task_text")
    acct = re.search(r"\naccount: (\d{10})\n", p); style = re.search(r"\nSTYLE: [^\n]+", p)
    if acct and style:
        for t, v in idx.items():
            if f"\naccount: {acct.group(1)}\n" in t and style.group(0) in t: return (*v, "account_style")
    return None, None, None, "unlinked"


# ---------------------------------------------------------------- collect: checks, review, keep
def to_row(world, lang, attempt, obj, dataset):
    row = W.make_row(world, lang, WRITER, obj)
    return row | {"writer": WRITER, "reviewer": REVIEWER, "attempt": attempt, "adaption_dataset": dataset}


def collect(out_files, name="test", dry=False):
    idx = task_index(split_dir(name)); kept_p, rej_p = W.paths(name)
    kept_before = W._read(kept_p); done = {r["id"] for r in kept_before}
    got, rejected, stats = [], [], Counter()
    for p in out_files:
        did = os.path.basename(p)
        for l in open(p):
            r = json.loads(l); stats["returned"] += 1
            wid, att, lang, how = link(r, idx); stats[f"link:{how}"] += 1
            if wid is None: rejected.append({"id": None, "reasons": ["unlinked"], "raw": r}); continue
            got.append((wid, att, lang, r, did))
    # one candidate per (world, attempt); earlier attempts first
    seen, cands = set(), []
    for wid, att, lang, r, did in sorted(got, key=lambda x: (W.world_index(x[0]), x[1])):
        if (wid, att) in seen: stats["duplicate_export_row"] += 1; continue
        seen.add((wid, att)); cands.append((wid, att, lang, r, did))
    passed = []; worlds = {}
    for wid, att, lang, r, did in cands:
        if wid in done: stats["already_kept"] += 1; continue
        w = worlds.setdefault(wid, g.sample_world(wid))
        obj = W.parse_json(_completion_of(r))
        if not isinstance(obj, dict) or "opening" not in obj:
            rejected.append({"id": wid, "lang": lang, "writer": WRITER, "attempt": att, "reasons": ["writer_bad_json"],
                             "raw_completion": _completion_of(r)[:2000], "adaption_dataset": did}); continue
        row = to_row(w, lang, att, obj, did); bad = W.code_checks(row, w)
        if bad: rejected.append({"id": wid, "lang": lang, "writer": WRITER, "attempt": att, "reasons": bad, "row": row}); continue
        passed.append(row)
    print(f"{len(cands)} candidates, {len(passed)} pass code checks; reviewing with {REVIEWER}", flush=True)
    if dry: return passed, rejected, stats
    # W.review keys labels by world id, so review in rounds: the earliest remaining attempt of each world not yet kept
    counts = Counter((r["lang"], W.norm_answer(a)) for r in kept_before for a in r["answers"].values())
    kept, kept_ids = [], set(done)
    queue = sorted(passed, key=lambda r: (W.world_index(r["id"]), r["attempt"]))
    while queue:
        rnd, rest, inround = [], [], set()
        for r in queue:
            if r["id"] in kept_ids: stats["later_attempt_not_needed"] += 1
            elif r["id"] in inround: rest.append(r)
            else: rnd.append(r); inround.add(r["id"])
        labels = W.review(rnd, REVIEWER) if rnd else {}
        for r in rnd:
            bad = W.compare(worlds[r["id"]], labels.get(r["id"])) or W.dup_check(r, counts)
            if bad:
                rejected.append({"id": r["id"], "lang": r["lang"], "writer": WRITER, "attempt": r["attempt"], "reasons": bad,
                                 "row": r, "review": labels.get(r["id"])}); continue
            kept.append(r); kept_ids.add(r["id"]); counts.update((r["lang"], W.norm_answer(a)) for a in r["answers"].values())
        queue = rest
    kept.sort(key=lambda r: W.world_index(r["id"]))
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(kept_p, "a") as f:
        for r in kept: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(rej_p, "a") as f:
        for r in rejected: f.write(json.dumps(r | {"prompt_version": W.PROMPT_VERSION, "t": stamp}, ensure_ascii=False) + "\n")
    report(kept, rejected, stats, kept_before)
    return kept, rejected, stats


def report(kept, rejected, stats, kept_before=()):
    print("export:", dict(stats))
    allk = list(kept_before) + list(kept)
    print("kept now:", len(kept), "| kept total:", len(allk), dict(Counter(r["lang"] for r in allk)))
    print("rejected rows by language:", dict(Counter(r.get("lang") for r in rejected)))
    reasons = Counter(re.sub(r"->.*", "", s) for r in rejected for s in set(r["reasons"]))
    print("rejection reasons (rows):", ", ".join(f"{k} {v}" for k, v in reasons.most_common(20)))


def topup_rows(name, ids, k):
    """k fresh attempts (new style seed, angles and pool picks) for each world in `ids` with no kept row yet,
    numbered after the highest attempt already sent for it."""
    kept = {r["id"] for r in W._read(W.paths(name)[0])}; sent = {}
    for p in glob.glob(os.path.join(split_dir(name), "tasks_*.jsonl")):
        for l in open(p):
            r = json.loads(l); sent[r["world_id"]] = max(sent.get(r["world_id"], -1), r["attempt"])
    rows = []
    for wid in ids:
        if wid in kept: continue
        for j in range(k): rows += task_rows([wid], sent.get(wid, -1) + 1 + j)
    return rows


def main(argv):
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    reg = lambda p: p.add_argument("--regime", default="base", choices=list(g.REGIMES),
                                   help="bankdesk_v4 regime the worlds are sampled under (shift-* worlds: shift)")
    t = sub.add_parser("tasks"); t.add_argument("--prefix", default="test"); t.add_argument("--start", type=int, default=0)
    t.add_argument("--n", type=int, default=300); t.add_argument("--attempts", type=int, default=1, help="attempts 0..k-1 per world")
    t.add_argument("--ids", help="file of world ids (overrides --prefix/--start/--n)"); t.add_argument("--out", required=True); reg(t)
    u = sub.add_parser("topup"); u.add_argument("--name", required=True); u.add_argument("--prefix", required=True)
    u.add_argument("--n", type=int, default=300); u.add_argument("--k", type=int, default=2); u.add_argument("--out", required=True); reg(u)
    l = sub.add_parser("launch"); l.add_argument("--file", required=True); l.add_argument("--name", required=True)
    l.add_argument("--dataset", help="reuse an uploaded dataset"); l.add_argument("--go", action="store_true")
    f = sub.add_parser("fetch"); f.add_argument("--dataset", required=True); f.add_argument("--out", required=True)
    c = sub.add_parser("collect"); c.add_argument("--out-files", nargs="+", required=True); c.add_argument("--name", default="test")
    c.add_argument("--dry", action="store_true"); reg(c)
    a = ap.parse_args(argv)
    if getattr(a, "regime", None): g.set_regime(a.regime)       # before any world is sampled
    if a.cmd in ("tasks", "topup"):
        if a.cmd == "tasks":
            ids = [x.strip() for x in open(a.ids) if x.strip()] if a.ids else [f"{a.prefix}-{i}" for i in range(a.start, a.start + a.n)]
            rows = [r for k in range(a.attempts) for r in task_rows(ids, k)]
        else: rows = topup_rows(a.name, [f"{a.prefix}-{i}" for i in range(a.n)], a.k)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{len(rows)} tasks ({len({r['world_id'] for r in rows})} worlds, regime {g.REGIME}, hash {g.params_hash()}) -> {a.out}",
              dict(Counter(r["lang"] for r in rows)))
    elif a.cmd == "launch": launch(a.file, a.name, a.go, a.dataset)
    elif a.cmd == "fetch": fetch(a.dataset, a.out)
    elif a.cmd == "collect": collect(a.out_files, a.name, a.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
