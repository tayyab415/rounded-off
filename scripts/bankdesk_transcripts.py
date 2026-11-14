"""Render BankDesk episodes as readable transcripts: customer request, each tool call with the agent's note and the
harness reply, then the scored outcome. Optionally compare each episode's tool sequence with an earlier run.

Usage: python scripts/bankdesk_transcripts.py EPISODES.jsonl CARDS.jsonl[,CARDS2.jsonl] OUT.md [--compare SAVED.jsonl]
"""
import argparse, collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd

ap = argparse.ArgumentParser()
ap.add_argument("episodes"); ap.add_argument("cards"); ap.add_argument("out"); ap.add_argument("--compare"); ap.add_argument("--title", default="")
a = ap.parse_args()

eps = [json.loads(l) for l in open(a.episodes, encoding="utf-8")]
cases = {}
for path in a.cards.split(","):
    for l in open(path, encoding="utf-8"):
        r = json.loads(l)
        for c in bd.cases_from_card(r["card"], r["card_id"], r["lang"]): cases[c.case_id] = c
saved = {}
if a.compare:
    for l in open(a.compare, encoding="utf-8"):
        r = json.loads(l); saved[r["case_id"]] = r

seq = lambda e: [t.get("tool") for t in e["turns"]]
tools = collections.Counter(t.get("tool") or "invalid" for e in eps for t in e["turns"])
n_turns = sum(len(e["turns"]) for e in eps)
scam = [e for e in eps if e["variant"] == "scam"]; gen = [e for e in eps if e["variant"] != "scam"]
L = [f"# {a.title or 'BankDesk transcripts'}", "",
     f"{len(eps)} episodes ({len(scam)} scam, {len(gen)} genuine), {n_turns} actions, "
     f"{sum(1 for e in eps for t in e['turns'] if not t.get('ok'))} rejected by the harness.", "",
     f"- Scams where money reached the scammer: {sum(bool(e['money_to_scammer']) for e in scam)} of {len(scam)}",
     f"- Scams held and escalated: {sum(e['end'] == 'escalated' for e in scam)} of {len(scam)}",
     f"- Genuine tasks completed: {sum(bool(e['completed']) for e in gen)} of {len(gen)}; "
     f"wrongly escalated: {sum(bool(e['false_escalation']) for e in gen)}",
     f"- Tool calls: " + ", ".join(f"{k} {v}" for k, v in tools.most_common())]
if saved:
    both = [e for e in eps if e["case_id"] in saved]
    same = sum(seq(e) == seq(saved[e["case_id"]]) for e in both)
    same_out = sum((e["end"], e["money_to_scammer"], e["completed"]) ==
                   (saved[e["case_id"]]["end"], saved[e["case_id"]]["money_to_scammer"], saved[e["case_id"]]["completed"]) for e in both)
    L.append(f"- Against the saved run ({os.path.basename(a.compare)}): same tool sequence in {same} of {len(both)}, "
             f"same outcome in {same_out} of {len(both)}")
L.append("")

for e in eps:
    c = cases.get(e["case_id"])
    kind = f"{e['variant']} ({e['clarity']})" + (", every bank check forced clean" if e.get("signals") == "clean" else "")
    L += [f"## {e['case_id']} | {e['lang'].upper()} | {e['family']} | {kind}", ""]
    if c: L += [f"**Customer:** {c.opening}", ""]
    for i, t in enumerate(e["turns"], 1):
        raw = t["raw"].strip().split("\n")
        act = raw[0].strip()
        note = " ".join(x.strip() for x in raw[1:] if x.strip())
        L.append(f"{i}. `{act[:220]}`" + ("" if t.get("ok") else "  **(rejected)**"))
        if note: L.append(f"   - agent: {note[:300]}")
        L.append(f"   - harness: {t['obs'][:300]}")
    if e["variant"] == "scam":
        res = "MONEY SENT TO SCAMMER" if e["money_to_scammer"] else ("held and escalated" if e["end"] == "escalated" else f"ended: {e['end']}")
    else:
        res = ("task completed" if e["completed"] else f"task not completed (ended: {e['end']})") + \
              (", wrongly escalated" if e["false_escalation"] else "")
    L += ["", f"**Outcome:** {res}; reward {e['reward']:.2f}", ""]
    if e["case_id"] in saved:
        s = saved[e["case_id"]]
        L += [f"Saved run: {' > '.join(str(x) for x in seq(s))} ({'same' if seq(s) == seq(e) else 'different'} tool sequence)", ""]

open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:12])); print("wrote", a.out)
