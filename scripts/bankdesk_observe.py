"""Observation tool for BankDesk: render the same cases, played by several agents, as readable side-by-side transcripts.

The point is to see how the harness behaves before tuning it: what each agent saw, what it did, what came back, and
how the rubric scored it. If a strong model behaves strangely, suspect the harness first.
Usage: python3 -I scripts/bankdesk_observe.py OUT.md CARDS.jsonl RUN1.jsonl [RUN2.jsonl ...] [--cases ID,ID | --sample N]
       [--filter "variant=genuine,end=escalated"]   (filter applies to the FIRST run)
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd
from bankdesk_run import load_cases

args = sys.argv[1:]
opt = lambda k, d=None: args[args.index(k) + 1] if k in args else d
out, cards = args[0], args[1]
runs = [a for a in args[2:] if a.endswith(".jsonl") and a != opt("--cases")]
cases = {c.case_id: c for c in load_cases(cards, "all")}
data = [{json.loads(l)["case_id"]: json.loads(l) for l in open(r, encoding="utf-8")} for r in runs]
names = [next(iter(d.values())).get("model", os.path.basename(r)) + "/" + next(iter(d.values())).get("system", "") for d, r in zip(data, runs)]

ids = list(data[0])
if opt("--filter"):
    conds = [c.split("=") for c in opt("--filter").split(",")]
    ids = [i for i in ids if all(str(data[0][i].get(k)) == v for k, v in conds)]
if opt("--cases"): ids = opt("--cases").split(",")
elif opt("--sample"): random.Random(0).shuffle(ids); ids = ids[:int(opt("--sample"))]

L = [f"# BankDesk transcripts ({len(ids)} cases)", "", f"Agents: {', '.join(names)}", ""]
for cid in ids:
    c = cases[cid]
    L += [f"## {cid} | {c.lang} | {c.family} | {c.variant} | {c.clarity}", "",
          "**What the agent sees first**", "", "```", bd.first_observation(c), "```", "",
          f"Hidden answers ({c.variant}): " + " / ".join(f"{k}: {v}" for k, v in c.answers.items()), ""]
    for d, n in zip(data, names):
        r = d.get(cid)
        if not r: continue
        L += [f"**{n}** — score {r['score']:+.1f}, end: {r['end']}, unsafe: {r['unsafe']}, completed: {r['completed']}, "
              f"rejected: {r['rejected']}", ""]
        for i, t in enumerate(r["turns"], 1):
            raw = t["raw"].strip().replace("\n", " ⏎ ")
            L.append(f"{i}. `{raw[:400]}`")
            back = t.get("error") or t.get("obs") or ""
            if back: L.append(f"   → {back[:300]}")
        L.append("")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"wrote {out}: {len(ids)} cases x {len(runs)} agents")
