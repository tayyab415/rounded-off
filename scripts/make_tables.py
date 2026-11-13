"""Pivot all judged outputs into the main results table (markdown + csv).

Rows: model tag (e.g. M1.w4). Columns: per metric, EN | HI value in percent with 95% CI in the csv.
Usage: python3 -I scripts/make_tables.py results/raw/judged2 results/main_table
"""
import sys, os, glob, csv, collections
sys.path.insert(0, os.path.dirname(__file__))
from summarize import summarize

src, out = sys.argv[1], sys.argv[2]
rows = summarize(sorted(glob.glob(os.path.join(src, "*.jsonl"))))
COLS = [("harmbench", "harmful_answer", "HarmBench harmful ↓"), ("xstest_unsafe", "harmful_answer", "XSTest-unsafe harmful ↓"),
        ("bank_redteam", "harmful_answer", "Bank red-team harmful ↓"),
        ("xstest_safe", "over_refusal", "XSTest-safe refused ↓"), ("bank_borderline", "over_refusal", "Bank borderline refused ↓"),
        ("bank_task", "qa_score", "Bank task score ↑"), ("rbi_qa", "qa_score", "RBI grounded ↑"),
        ("rbi_qa_unanswerable", "abstain_ok", "RBI abstains when unanswerable ↑")]
cell = {(r["model"], r["set"], r["lang"], r["metric"]): r for r in rows}
broken = collections.defaultdict(list)
for r in rows:
    if r["set"] in ("xstest_safe", "bank_borderline", "bank_task"): broken[(r["model"], r["lang"])].append(r["broken"])
ORDER = ["bf16", "w4", "w3g32", "w3"]
def _key(m):
    base, _, prec = m.partition(".")
    return (base, ORDER.index(prec) if prec in ORDER else 9, m)
models = sorted({r["model"] for r in rows}, key=_key)
present = [c for c in COLS if any((m, c[0], l, c[1]) in cell for m in models for l in ("en", "hi"))]
fmt = lambda r: "–" if r is None else f"{100*r['value']:.1f}"
with open(out + ".md", "w") as f:
    f.write("| model | " + " | ".join(f"{c[2]} EN / HI" for c in present) + " | broken (benign+task) EN / HI |\n")
    f.write("|---" * (len(present) + 2) + "|\n")
    for m in models:
        cells = [f"{fmt(cell.get((m, s, 'en', k)))} / {fmt(cell.get((m, s, 'hi', k)))}" for s, k, _ in present]
        b = [f"{100*sum(broken[(m, l)])/len(broken[(m, l)]):.1f}" if broken[(m, l)] else "–" for l in ("en", "hi")]
        f.write(f"| {m} | " + " | ".join(cells) + f" | {b[0]} / {b[1]} |\n")
with open(out + ".csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + [k for k in ("partial", "wrong", "not_found") if k not in rows[0]],
                       extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print(open(out + ".md").read())
