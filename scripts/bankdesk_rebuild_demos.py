"""Rebuild SFT demos from the teacher's saved trajectories under the current simulator rules (exact replay).

A trajectory whose replay differs before its end (a non-terminal reply that now parses or passes differently) is
dropped, since the teacher would have seen different observations. Kept trajectories pass the same `keep` test as
bankdesk_teacher.py. A terminal message cut off by the token limit is trimmed to its last full sentence and closed,
so the student is not trained on half sentences.
Usage: python3 -I scripts/bankdesk_rebuild_demos.py CARDS.jsonl TEACHER.all.jsonl OUT.jsonl
"""
import collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd
from bankdesk_run import load_cases
from bankdesk_teacher import keep

cards, src, dst = sys.argv[1:4]
cases = {c.case_id: c for c in load_cases(cards, "all")}
stats = collections.Counter(); out = []
for line in open(src, encoding="utf-8"):
    r = json.loads(line); ep = bd.Episode(cases[r["case_id"]]); diverged = False
    for t in r["turns"]:
        if ep.done: break
        ep.step(t["raw"]); new = ep.log[-1]
        if new["ok"] != t["ok"] and new["tool"] not in bd.TERMINAL: diverged = True; break
    if diverged or not ep.done: stats[(r["lang"], "dropped: replay diverged")] += 1; continue
    ok, why = keep(ep); stats[(r["lang"], why)] += 1
    if not ok: continue
    for rec in ep.log:
        if rec["tool"] in bd.TERMINAL and rec["args"].get("_truncated"):
            key = bd.TOOLS[rec["tool"]][0]; text = rec["args"][key]
            cut = max(text.rfind("।"), text.rfind(". "), text.rfind("।"), text.rfind("? "), text.rfind("! "))
            text = (text[:cut + 1] if cut > 20 else text).strip()
            rec["raw"] = f'ACTION: {rec["tool"]}({key}="{text}")'
    c = ep.case
    out.append({"case_id": c.case_id, "lang": c.lang, "family": c.family, "variant": c.variant, "clarity": c.clarity,
                "messages": bd.messages(ep)})
with open(dst, "w", encoding="utf-8") as f:
    for o in out: f.write(json.dumps(o, ensure_ascii=False) + "\n")
print(f"kept {len(out)}")
for k, n in sorted(stats.items()): print(" ", k, n)
print(dict(collections.Counter((o["lang"], o["variant"], o["clarity"]) for o in out)))
