"""BankDesk results table from *.summary.json (scripts/bankdesk_run.py) with 95% bootstrap intervals from the
episode files when available. Usage: python3 -I scripts/bankdesk_tables.py RESULTS_DIR [EPISODES_DIR ...] > OUT.md"""
import glob, json, os, random, sys
def ci(xs, n=2000):
    if not xs: return None
    rnd = random.Random(0); m = sum(xs) / len(xs); bs = sorted(sum(rnd.choices(xs, k=len(xs))) / len(xs) for _ in range(n))
    return m, bs[50], bs[1949]
eps = {}
for d in sys.argv[2:]:
    for f in glob.glob(os.path.join(d, "*.jsonl")):
        for l in open(f):
            r = json.loads(l); eps.setdefault((r["model"], r["system"]), []).append(r)
fmt = lambda c: "–" if c is None else f"{100*c[0]:.1f} [{100*c[1]:.0f}–{100*c[2]:.0f}]"
print("| model | prompt | lang | unsafe on scam cases | escalated scam | genuine task done | false escalation | rejected actions / episode |")
print("|---|---|---|---|---|---|---|---|")
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.summary.json"))):
    d = json.load(open(f)); E = eps.get((d["tag"], d["system"]), [])
    for l in ("en", "hi"):
        sc = [r for r in E if r["lang"] == l and r["variant"] == "scam"]; ge = [r for r in E if r["lang"] == l and r["variant"] == "genuine"]
        rows = {(r["group"], r["lang"]): r for r in d["rows"]}
        u = ci([int(r["unsafe"]) for r in sc]) or (rows[("scam", l)]["unsafe"],) * 3
        e = ci([int(r["end"] == "escalated" and not r["unsafe"]) for r in sc]) or (rows[("scam", l)]["escalated_scam"],) * 3
        c = ci([int(r["completed"]) for r in ge]) or (rows[("genuine", l)]["completed"],) * 3
        fe = ci([int(r["false_escalation"]) for r in ge]) or (rows[("genuine", l)]["false_escalation"],) * 3
        print(f"| {d['tag']} | {d['system']} | {l.upper()} | {fmt(u)} | {fmt(e)} | {fmt(c)} | {fmt(fe)} | {rows[('all', l)]['rejected_per_ep']:.2f} |")
