"""Run the AuditKIT release gate over every baseline -> candidate pair that has results, and write one summary.

Pairs: each full-precision model vs its quantized copies (does the model survive compression?), each fine-tune vs the
original, and each repair vs the model it repairs. Output: results/gates/<base>__<cand>.json + results/gates/SUMMARY.md
Usage: python scripts/run_gates.py results/raw/judged2
"""
import glob, json, os, subprocess, sys
src = sys.argv[1]; out = "results/gates"; os.makedirs(out, exist_ok=True)
tags = sorted({os.path.basename(p).split(".en")[0].split(".hi")[0] for p in glob.glob(os.path.join(src, "*.jsonl"))})
have = set(tags)
pairs = []
for t in tags:
    base, _, prec = t.partition(".")
    if prec == "bf16":
        for c in tags:
            if c.startswith(base + ".") and c != t: pairs.append((t, c))
for a, b in [("M0.bf16", "M1.bf16"), ("M0.bf16", "C1.bf16"), ("C1.bf16", "C2_safegrad.bf16")] + \
            [("M1.bf16", t) for t in tags if t.startswith("R_") and t.endswith(".bf16")] + \
            [("C1.bf16", t) for t in tags if t.startswith("CR_") and t.endswith(".bf16")]:
    if a in have and b in have: pairs.append((a, b))
lines = ["| baseline | candidate | harmful (refusal/harm sets) | benign (over-refusal) | qa (task) |", "|---|---|---|---|---|"]
for a, b in pairs:
    f = os.path.join(out, f"{a}__{b}.json")
    subprocess.run([sys.executable, "scripts/ak_gate.py", "--base", a, "--cand", b, "--dir", src, "--out", f],
                   check=True, capture_output=True)
    rep = json.load(open(f))["candidates"][b]
    g = lambda fam: rep.get(fam, {}).get("grade", "–").replace("DeltaGrade.", "")
    lines.append(f"| {a} | {b} | {g('harmful')} | {g('benign')} | {g('qa')} |")
open(os.path.join(out, "SUMMARY.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
