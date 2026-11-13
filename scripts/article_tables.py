"""Compact tables for the article, grouped by question. Cells are "EN / HI" in percent; 95% CIs are in main_table*.csv.

Usage: python3 -I scripts/article_tables.py results/raw/judged2 results/article_tables.md [RESTA_TAG]
RESTA_TAG is the contaminated RESTA setting picked by select_repair.py (default CR_resta25).
"""
import collections, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summarize import summarize

src, out = sys.argv[1], sys.argv[2]
resta = sys.argv[3] if len(sys.argv) > 3 else "CR_resta25"
rows = summarize(sorted(glob.glob(os.path.join(src, "*.jsonl"))))
cell = {(r["model"], r["set"], r["lang"], r["metric"]): r for r in rows}
broken = collections.defaultdict(list)
for r in rows:
    if r["set"] in ("xstest_safe", "bank_borderline", "bank_task"): broken[(r["model"], r["lang"])].append(r["broken"])
COLS = [("harmbench", "harmful_answer", "HarmBench harmful ↓"), ("bank_redteam", "harmful_answer", "Bank red-team harmful ↓"),
        ("xstest_safe", "over_refusal", "XSTest-safe refused ↓"), ("bank_borderline", "over_refusal", "Bank borderline refused ↓"),
        ("bank_task", "qa_score", "Bank task ↑"), ("rbi_qa", "qa_score", "RBI grounded ↑")]
P = ["bf16", "w4", "w3g32"]
GROUPS = [
    ("Benign fine-tune: original (M0), bank fine-tune (M1), WiSE-FT repair (R_wise50)",
     [f"{m}.{p}" for m in ("M0", "M1", "R_wise50") for p in P]),
    (f"Contaminated fine-tune (C1) and its repairs: WiSE-FT, RESTA ({resta}), SafeGrad (train-time)",
     [f"{m}.{p}" for m in ("C1", "CR_wise50", resta, "C2_safegrad") for p in P]),
    ("Layer protection at 3-bit: CR_wise50 W3 g32 with 6 layers kept in bf16",
     ["CR_wise50.w3g32"] + [f"CR_wise50.w3g32_{a}" for a in ("ck6", "edge6", "rnd1", "rnd2", "rnd3")]),
    ("Closed-model reference", ["LUNA.api"]),
    ("Every repair setting at bf16 (selection rule input)",
     sorted({r["model"] for r in rows if r["model"].endswith(".bf16") and r["model"].split(".")[0].startswith(("R_", "CR_"))})),
]
fmt = lambda r: "–" if r is None else f"{100*r['value']:.1f}"
lines = []
for title, models in GROUPS:
    models = [m for m in models if any(k[0] == m for k in cell)]
    if not models: continue
    lines += [f"### {title}", "", "| model | " + " | ".join(c[2] for c in COLS) + " | broken |", "|---" * (len(COLS) + 2) + "|"]
    for m in models:
        cs = [f"{fmt(cell.get((m, s, 'en', k)))} / {fmt(cell.get((m, s, 'hi', k)))}" for s, k, _ in COLS]
        b = [f"{100*sum(broken[(m, l)])/len(broken[(m, l)]):.1f}" if broken[(m, l)] else "–" for l in ("en", "hi")]
        lines.append(f"| {m} | " + " | ".join(cs) + f" | {b[0]} / {b[1]} |")
    lines.append("")
open(out, "w").write("Cells: EN / HI, percent. broken = mean broken rate over XSTest-safe, bank borderline, bank task.\n\n"
                     + "\n".join(lines))
print(open(out).read())
