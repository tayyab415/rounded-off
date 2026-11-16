"""Story figures for the article (numbers copied from the results files named next to each block).

  python3 scripts/plot_story.py      # writes article/figures/{agents,ladder,repairs}.{svg,png}
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
ORANGE, BLUE, GREY, GREEN = "#eb6834", "#2a78d6", "#a8a6a0", "#1f9d6a"
plt.rcParams.update({"font.family": ["Avenir Next", "Helvetica Neue", "DejaVu Sans"], "font.size": 10.5, "svg.fonttype": "path",
                     "axes.titlepad": 10})
OUT = "article/figures/"

def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)

def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(OUT + name + "." + ext, dpi=200, facecolor=SURF, bbox_inches="tight")
    print("wrote", name)

# 1. Who decides: scams paid (left) vs genuine customers blocked (right), EN and HI.
# results/bankdesk_v3/RULES_BASELINE.md (normal checks) and results/bankdesk_v3/BIG_MODELS.md
rows = [("repaired chat model, given tools (R_wise50)", 94.8, 83.0, 1.5, 0.0, GREY),
        ("rule: strongest signs only", 49.3, 52.3, 3.0, 6.8, BLUE),
        ("rule: hold on two flags", 35.8, 36.4, 11.9, 6.8, BLUE),
        ("rule: hold if any check flags", 11.9, 6.8, 34.3, 36.4, BLUE),
        ("GLM-5.3-Flash (big open model, our teacher)", 11.2, 12.5, 28.4, 25.0, GREY),
        ("DeepSeek-V4.1-Flash (big open model)", 5.2, 3.4, 21.6, 17.0, GREY),
        ("our trained Tiny Aya agent, 3.35B (GRPO3)", 0.7, 2.3, 3.7, 2.3, ORANGE)]
fig, (axl, axr) = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True, facecolor=SURF, gridspec_kw={"wspace": 0.04})
y = list(range(len(rows)))[::-1]; h = 0.36
for yi, (name, pe, ph, be, bh, c) in zip(y, rows):
    axl.barh(yi + h / 2, pe, h, color=c); axl.barh(yi - h / 2, ph, h, color=c, alpha=0.45)
    axr.barh(yi + h / 2, be, h, color=c); axr.barh(yi - h / 2, bh, h, color=c, alpha=0.45)
    axl.text(pe + 1.5, yi + h / 2, f"{pe:.1f}", va="center", ha="right", fontsize=8, color=INK2)
    axr.text(be + 0.8, yi + h / 2, f"{be:.1f}", va="center", fontsize=8, color=INK2)
for ax in (axl, axr): ax.axhspan(-0.5, 0.5, color=ORANGE, alpha=0.08, zorder=0)
axl.set_xlim(105, 0); axr.set_xlim(0, 45)
axl.set_yticks(y); axl.set_yticklabels([r[0] for r in rows], color=INK)
axl.get_yticklabels()[-1].set_fontweight("bold")
for ax in (axl, axr): style(ax); ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
axl.set_title("scams paid, %  (lower is better)", loc="right", color=INK, fontsize=10.5, fontweight="bold")
axr.set_title("genuine customers blocked, %  (lower is better)", loc="left", color=INK, fontsize=10.5, fontweight="bold")
axl.spines["left"].set_visible(False); axr.tick_params(axis="y", left=False)
fig.suptitle("Same 111 held-out test cards: only the trained agent is low on both sides", x=0.02, ha="left",
             fontsize=12.5, fontweight="bold", color=INK, y=1.08)
fig.text(0.02, 1.0, "solid bar = English (134 scam, 134 genuine cases), light bar = Hindi (88 + 88)", color=INK2, fontsize=9)
save(fig, "agents"); plt.close(fig)

# 2. Training ladder: scams paid at each step, normal checks and every check clean. results/bankdesk_v3/FINAL_TEST.md
steps = ["repaired\nchat model", "+ strong\nprompt", "+ SFT\n(teacher)", "+ DPO", "+ GRPO\n(unsure states)"]
en = [94.8, 91.0, 6.0, 3.7, 0.7]; hi = [83.0, 80.7, 5.7, 5.7, 2.3]
cen = [98.5, None, 48.5, 37.3, 21.6]; chi = [77.3, None, 60.2, 52.3, 31.8]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True, facecolor=SURF)
for ax, (a, b, title) in zip(axes, [(en, hi, "normal bank checks"), (cen, chi, "every bank check forced clean (only asking catches the scam)")]):
    xs = [i for i, v in enumerate(a) if v is not None]
    ax.bar([x - 0.19 for x in xs], [a[x] for x in xs], 0.38, color=[ORANGE if x == 4 else GREY for x in xs])
    ax.bar([x + 0.19 for x in xs], [b[x] for x in xs], 0.38, color=[ORANGE if x == 4 else GREY for x in xs], alpha=0.45)
    for x in xs:
        ax.text(x - 0.19, a[x] + 1.5, f"{a[x]:.1f}", ha="center", fontsize=8, color=INK)
        ax.text(x + 0.19, b[x] + 1.5, f"{b[x]:.1f}", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(range(len(steps))); ax.set_xticklabels(steps, fontsize=8.5, color=INK)
    style(ax); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.set_ylim(0, 108)
    ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold", color=INK)
    ax.axvspan(3.5, 4.5, color=ORANGE, alpha=0.08, zorder=0)
axes[0].set_ylabel("scams where the money reached the scammer, %", color=INK2, fontsize=9)
axes[1].text(1, 4, "not run", ha="center", fontsize=8, color=INK2)
fig.suptitle("Each training step cuts scam payments; GRPO is what teaches the agent to ask", x=0.02, ha="left",
             fontsize=12.5, fontweight="bold", color=INK, y=1.07)
fig.text(0.02, 0.995, "solid = English, light = Hindi; 111 held-out test cards", color=INK2, fontsize=9)
save(fig, "ladder"); plt.close(fig)

# 3. Repairs fix the benchmark, not the bank: slope chart, C1 -> CR_wise50 (English). results/main_table_v3.csv
fig, ax = plt.subplots(figsize=(6.4, 4.4), facecolor=SURF)
for label, a, b, c in [("HarmBench (generic benchmark)", 59.3, 16.7, BLUE), ("our bank fraud red-team", 68.4, 52.8, ORANGE)]:
    ax.plot([0, 1], [a, b], color=c, lw=2.5, marker="o", markersize=8)
    ax.text(-0.04, a, f"{a:.1f}", ha="right", va="center", color=INK, fontsize=9.5)
    ax.text(1.04, b, f"{b:.1f}  {label}", ha="left", va="center", color=c, fontsize=9.5, fontweight="bold")
ax.text(0.56, 27, "−72%", color=BLUE, fontsize=11, fontweight="bold", ha="center")
ax.text(0.5, 64, "−23%", color=ORANGE, fontsize=11, fontweight="bold", ha="center")
ax.set_xticks([0, 1]); ax.set_xticklabels(["contaminated\nfine-tune (C1)", "after WiSE-FT\nrepair (CR_wise50)"], color=INK)
ax.set_xlim(-0.35, 1.9); ax.set_ylim(0, 80); style(ax); ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.set_title("The repair fixes the benchmark, not the bank\nharmful answers, English, %", loc="left", fontsize=12, fontweight="bold", color=INK)
save(fig, "repairs"); plt.close(fig)
