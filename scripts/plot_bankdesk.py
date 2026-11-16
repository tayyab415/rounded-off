"""Figure for the agent result: scams paid against genuine customers blocked, models and bank rules.

Reads the table in results/bankdesk_v3/RULES_BASELINE.md (normal checks only) and writes article/figures/bankdesk.png.
  python3 scripts/plot_bankdesk.py [OUT.png]
"""
import re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "results/bankdesk_v3/RULES_BASELINE.md"
OUT = sys.argv[1] if len(sys.argv) > 1 else "article/figures/bankdesk.png"
MODEL, RULE = "#eb6834", "#2a78d6"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SHOW = {  # agent -> (label, colour, label offset in points)
    "R_wise50": ("before agent training\n(R_wise50)", MODEL, (8, -4)),
    "GRPO3": ("after agent training\n(GRPO3)", MODEL, (10, 6)),
    "R_any": ("rule: hold if any flag", RULE, (8, 16)),
    "R_two": ("rule: hold on two flags", RULE, (8, 0)),
    "R_narrow": ("rule: strongest signs only", RULE, (8, 0)),
}


def cell(s):
    m = re.match(r"([\d.]+) \[([\d.]+)–([\d.]+)\]", s.strip())
    return tuple(float(x) for x in m.groups())


rows = {}
for line in open(SRC, encoding="utf-8"):
    p = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(p) == 6 and p[0] in SHOW and p[1] == "normal":
        rows[(p[0], p[2])] = {"paid": cell(p[3]), "blocked": cell(p[5])}
assert len(rows) == 10, rows.keys()

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True, facecolor=SURF)
for ax, (lang, title) in zip(axes, [("EN", "English (134 scam, 134 genuine cases)"), ("HI", "Hindi (88 scam, 88 genuine cases)")]):
    ax.set_facecolor(SURF)
    for agent, (label, colour, off) in SHOW.items():
        r = rows[(agent, lang)]
        (x, xl, xh), (y, yl, yh) = r["blocked"], r["paid"]
        ax.plot([xl, xh], [y, y], color=colour, lw=1.2, alpha=0.45, zorder=2)
        ax.plot([x, x], [yl, yh], color=colour, lw=1.2, alpha=0.45, zorder=2)
        ax.scatter([x], [y], s=70, color=colour, edgecolor=SURF, linewidth=2, zorder=3)
        ax.annotate(f"{label}\n{y:.1f}% paid, {x:.1f}% blocked", (x, y), xytext=off, textcoords="offset points",
                    fontsize=8.3, color=INK, va="center", ha="left" if off[0] >= 0 else "right", zorder=4)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")
    ax.set_xlim(-2, 60); ax.set_ylim(-3, 103)
    ax.set_xticks(range(0, 61, 10)); ax.set_xticklabels([f"{v}%" for v in range(0, 61, 10)], color=INK2)
    ax.set_yticks(range(0, 101, 20)); ax.set_yticklabels([f"{v}%" for v in range(0, 101, 20)], color=INK2)
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(axis="both", length=0)
    ax.set_xlabel("genuine customers blocked (escalated to the fraud team)", color=INK2, fontsize=9)
axes[0].set_ylabel("scam cases where the money reached the scammer", color=INK2, fontsize=9)
handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=8, label=n)
           for n, c in [("Tiny Aya agent", MODEL), ("bank rule on the same two checks", RULE)]]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.005, 0.95), ncol=2, frameon=False, fontsize=9.5)
fig.suptitle("Rules trade scams paid for customers blocked; the trained agent avoids the trade", x=0.01, y=0.99,
             ha="left", fontsize=12, color=INK, fontweight="bold")
fig.text(0.99, 0.01, "BankDesk test, 111 held-out cards, normal (noisy) bank checks; bars = 95% CI resampling cards. "
         "With every check clean, every rule pays every scammer.", ha="right", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 0.89))
fig.savefig(OUT, dpi=200, facecolor=SURF)
print("wrote", OUT)
