"""Headline figure: HarmBench vs bank red-team harmful-answer rate for each model, English and Hindi side by side.

One row per model, two dots (generic benchmark, bank red-team) joined by a line; the line is the gap a generic check misses.
Bars show 95% bootstrap intervals from main_table*.csv.
Usage: python3 scripts/plot_headline.py results/main_table_v3.csv article/figures/headline.png
"""
import csv, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src, out = sys.argv[1], sys.argv[2]
ROWS = [  # (tag, label); None = group heading
    (None, "Clean fine-tune"),
    ("M0.bf16", "Tiny Aya Global (M0)"), ("M1.bf16", "bank fine-tune (M1)"),
    ("R_wise50.bf16", "M1 + WiSE-FT"), ("R_wise50.w4", "M1 + WiSE-FT, 4-bit"),
    (None, "Fine-tune with 10% harmful data"),
    ("C1.bf16", "contaminated (C1)"), ("CR_wise50.bf16", "C1 + WiSE-FT"), ("CR_wise50.w4", "C1 + WiSE-FT, 4-bit"),
    ("CR_resta10.bf16", "C1 + RESTA (rule pick)"), ("C2_safegrad.bf16", "SafeGrad (train-time)"),
    (None, "Trained as an agent (BankDesk)"),
    ("GRPO3.bf16", "M1 + WiSE-FT + SFT + GRPO"),
    (None, "Closed model"),
    ("LUNA.api", "GPT-6 Luna"),
]
SETS = [("harmbench", "HarmBench (generic)", "#2a78d6"), ("bank_redteam", "Bank red-team (ours)", "#eb6834")]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

cell = {}
for r in csv.DictReader(open(src)):
    if r["metric"] == "harmful_answer":
        cell[(r["model"], r["set"], r["lang"])] = tuple(100 * float(r[k]) for k in ("value", "lo", "hi"))
rows = [(t, l) for t, l in ROWS if t is None or any((t, s, "en") in cell for s, _, _ in SETS)]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, axes = plt.subplots(1, 2, figsize=(11, 0.36 * len(rows) + 1.3), sharey=True, facecolor=SURF)
ys = list(range(len(rows)))[::-1]
for ax, lang, title in zip(axes, ("en", "hi"), ("English", "Hindi")):
    ax.set_facecolor(SURF)
    for y, (tag, label) in zip(ys, rows):
        if tag is None: continue
        pts = [cell.get((tag, s, lang)) for s, _, _ in SETS]
        if all(pts): ax.plot([pts[0][0], pts[1][0]], [y, y], color=GRID, lw=3, zorder=1, solid_capstyle="round")
        for p, (_, _, c) in zip(pts, SETS):
            if not p: continue
            ax.plot([p[1], p[2]], [y, y], color=c, lw=1.2, alpha=0.45, zorder=2)
            ax.scatter([p[0]], [y], s=64, color=c, edgecolor=SURF, linewidth=2, zorder=3)
        if pts[1]: ax.text(pts[1][2] + 1.5, y, f"{pts[1][0]:.0f}%", va="center", fontsize=8.5, color=INK2)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")
    ax.set_xlim(-2, 82); ax.set_xticks(range(0, 81, 20)); ax.set_xticklabels([f"{x}%" for x in range(0, 81, 20)], color=INK2)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(axis="both", length=0)
    ax.set_xlabel("harmful answers (coherent reply judged unsafe)", color=INK2, fontsize=9)
axes[0].set_yticks(ys)
axes[0].set_yticklabels([l if t else l.upper() for t, l in rows], color=INK)
for lab, (t, _) in zip(axes[0].get_yticklabels(), rows):
    if t is None: lab.set_fontsize(8); lab.set_color(INK2); lab.set_fontweight("bold")
handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=8, label=n) for _, n, c in SETS]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.01, 0.995), ncol=2, frameon=False, fontsize=9.5)
fig.suptitle("Repairs fix the benchmark, not the bank", x=0.99, y=0.995, ha="right", fontsize=12, color=INK, fontweight="bold")
fig.text(0.99, 0.005, "Tiny Aya Global 3.35B; greedy; judges Qwen3Guard-Gen-8B + Qwen3-8B; bars = 95% bootstrap CI",
         ha="right", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.02, 1, 0.965))
fig.savefig(out, dpi=200, facecolor=SURF)
print("wrote", out)
