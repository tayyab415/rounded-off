"""Assemble the fine-tuning set and the two task evals.

Fine-tuning (publishable): Banking77 train queries (CC-BY-4.0) + Adaption answers, English originals and hi-IN rows.
  -> sft_raw.jsonl  {"messages": [...], "meta": {...}}
Bank task eval: Banking77 *test* queries (4/intent) + Adaption reference answers, EN and hi-IN.
  -> bank_task_{en,hi}.jsonl  (kind=qa, reference=Adaption answer)
RBI grounded-reading eval (RBI text is not redistributed; only ids/URLs are published):
  150 EN/HI *pairs* (same FAQ in both languages). Context = 3 answers from the same FAQ document, shuffled.
  80% answerable (target answer is among the 3); 20% unanswerable (target removed) -> the right reply is "I don't know".
  -> rbi_qa_{en,hi}.jsonl  (kind=qa, answerable flag, reference=official answer or NOT_IN_CONTEXT)
Usage: python3 -I scripts/build_data.py --b77 B77.jsonl --b77-test B77TEST.jsonl --rbi-en EN.jsonl --rbi-hi HI.jsonl --out DIR
"""
import argparse, json, random, collections, pathlib, os

ap = argparse.ArgumentParser()
ap.add_argument("--b77", required=True); ap.add_argument("--b77-test"); ap.add_argument("--rbi-en", required=True)
ap.add_argument("--rbi-hi", required=True); ap.add_argument("--out", required=True); ap.add_argument("--n-pairs", type=int, default=150)
a = ap.parse_args()
rnd = random.Random(13); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)

def adaption_rows(p):
    for l in open(p):
        r = json.loads(l)
        q = (r.get("prompt") or r.get("customer_query") or "").strip()
        ans = (r.get("enhanced_completion") or r.get("completion") or "").strip()
        if q and ans and ans != "None":
            yield ("hi" if str(r.get("target_language_code", "")).startswith("hi") else "en"), q, ans, r

# 1) fine-tuning rows
n = collections.Counter(); rows = []
for lang, q, ans, r in adaption_rows(a.b77):
    rows.append({"messages": [{"role": "user", "content": q}, {"role": "assistant", "content": ans}],
                 "meta": {"source": "banking77+adaption", "lang": lang, "intent": r.get("intent")}}); n["sft_" + lang] += 1
rnd.shuffle(rows)
with open(out / "sft_raw.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")

# 2) bank task eval
if a.b77_test and os.path.exists(a.b77_test):
    fh = {l: open(out / f"bank_task_{l}.jsonl", "w") for l in ("en", "hi")}
    for i, (lang, q, ans, r) in enumerate(adaption_rows(a.b77_test)):
        fh[lang].write(json.dumps({"id": f"b77t-{i}", "lang": lang, "set": "bank_task", "kind": "qa", "prompt": q,
                                   "reference": ans, "answerable": True, "intent": r.get("intent")}, ensure_ascii=False) + "\n")
        n["bank_task_" + lang] += 1

# 3) RBI paired grounded-reading eval
rbi = {l: [json.loads(x) for x in open(p)] for l, p in (("en", a.rbi_en), ("hi", a.rbi_hi))}
by_doc = {l: collections.defaultdict(list) for l in rbi}
for l, rs in rbi.items():
    for r in rs: by_doc[l][r["doc_id"]].append(r)
pairs = collections.defaultdict(dict)
for l, rs in rbi.items():
    for r in rs:
        if r.get("pair_id") and 60 <= len(r["answer"]) <= 1500: pairs[r["pair_id"]][l] = r
pids = sorted(p for p, d in pairs.items() if len(d) == 2 and len(by_doc["en"][d["en"]["doc_id"]]) >= 4)
rnd.shuffle(pids); pids = pids[: a.n_pairs]
fr = {l: open(out / f"rbi_qa_{l}.jsonl", "w") for l in ("en", "hi")}
for k, pid in enumerate(pids):
    answerable = k % 5 != 0          # every 5th pair is unanswerable
    seed = rnd.random()
    for l in ("en", "hi"):
        tgt = pairs[pid][l]
        others = [x for x in by_doc[l][tgt["doc_id"]] if x["id"] != tgt["id"] and len(x["answer"]) <= 1500]
        rr = random.Random(f"{pid}-{seed}")       # same choice of distractor positions in both languages
        ctx_rows = rr.sample(others, k=2 if answerable else 3) + ([tgt] if answerable else [])
        rr.shuffle(ctx_rows)
        ctx = "\n\n".join(f"- {x['answer']}" for x in ctx_rows)
        fr[l].write(json.dumps({"id": f"rbi-{pid}", "lang": l, "set": "rbi_qa", "kind": "qa", "prompt": tgt["question"],
                                "context": ctx, "reference": tgt["answer"] if answerable else "NOT_IN_CONTEXT",
                                "answerable": answerable, "source_url": tgt["source_url"], "doc_id": tgt["doc_id"]},
                               ensure_ascii=False) + "\n")
        n[f"rbi_{l}_{'ans' if answerable else 'unans'}"] += 1
print(dict(n))
