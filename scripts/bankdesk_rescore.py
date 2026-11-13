"""Re-score saved BankDesk episodes with the current simulator code, exactly.

The simulator is deterministic, so replaying an episode's saved agent replies reproduces every observation the agent
saw, as long as each reply parses the same way. The only parser change (2026-11-13: a terminal action cut off by the
token limit is accepted) can only END an episode earlier at a reply that used to be rejected; the replay stops there
and drops the later replies, which the agent would never have written. Any other parse difference is reported.
Usage: python3 -I scripts/bankdesk_rescore.py CARDS.jsonl IN.jsonl OUT.jsonl
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd
from bankdesk_customer import llm_customer        # replays hit the answer cache, so they cost nothing
from bankdesk_run import load_cases, summarize, print_table

cards, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
cases = {c.case_id: c for c in load_cases(cards, "all")}
changed = diverged = 0; recs = []
for line in open(src, encoding="utf-8"):
    r = json.loads(line)
    ep = bd.Episode(cases[r["case_id"]], llm_customer if r.get("customer") == "llm" else None)
    for i, t in enumerate(r["turns"]):
        if ep.done: break
        obs = ep.step(t["raw"])
        new = ep.log[-1]
        if new["ok"] != t["ok"] and not (new["tool"] in bd.TERMINAL): diverged += 1
    nr = ep.record() | {k: r[k] for k in r if k in ("model", "system", "kept", "why")}
    if (nr["score"], nr["end"]) != (r["score"], r["end"]): changed += 1
    recs.append(nr)
with open(dst, "w", encoding="utf-8") as f:
    for nr in recs: f.write(json.dumps(nr, ensure_ascii=False) + "\n")
print(f"{src}: {len(recs)} episodes, {changed} outcomes changed, {diverged} non-terminal parse differences")
if recs and "model" in recs[0]: print_table(summarize(recs), f"{recs[0]['model']} {recs[0].get('system', '')} (re-scored)")
