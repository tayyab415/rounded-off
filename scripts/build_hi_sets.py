"""Split Adaption's Hindi translations of the public eval prompts into per-set JSONL files.

Keeps rows whose ids match the English sets; drops rows containing characters outside
Devanagari, Latin, digits and punctuation (translation glitches such as stray Cyrillic).
Usage: python3 -I scripts/build_hi_sets.py data/adaption/public_eval_hi.jsonl data/eval
"""
import json, re, sys, collections, pathlib
src, out = sys.argv[1], pathlib.Path(sys.argv[2])
OK = re.compile(r"^[ऀ-ॿ -~ -ÿ‐-‧₹\s]*$")
by_set, dropped = collections.defaultdict(list), []
for l in open(src):
    r = json.loads(l)
    if not str(r.get("target_language_code", "")).startswith("hi"): continue
    p = (r["prompt"] or "").strip()
    if not OK.match(p):
        dropped.append((r["id"], p[:80])); continue
    by_set[r["set"]].append({"id": r["id"], "lang": "hi", "set": r["set"], "kind": r["kind"], "category": r["category"],
                             "prompt": p, "source": r["source"] + " / Hindi translation by Adaption"})
for s, rows in by_set.items():
    with open(out / f"{s}_hi.jsonl", "w") as f:
        for r in sorted(rows, key=lambda x: x["id"]): f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(s, len(rows))
print("dropped", len(dropped), dropped[:5])
