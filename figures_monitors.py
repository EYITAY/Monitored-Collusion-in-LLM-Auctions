import csv, json, os, sys, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

if len(sys.argv) < 4:
    sys.exit("Usage: python figures_monitors.py data/main.jsonl data/main.rescore_deepseek_deepseek_chat.jsonl data/main.rescore_modal_qwen.jsonl")
GAMES, DS, QW = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = "figures"
os.makedirs(OUT, exist_ok=True)
CONDS = ["neutral", "collude_open", "collude_monitored"]
LABEL = {"neutral": "neutral", "collude_open": "collude\nopen", "collude_monitored": "collude\nmonitored"}
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.axisbelow": True,
})
rng = np.random.default_rng(0)


def load(path):
    return [json.loads(l) for l in open(path)]


games = load(GAMES)
ds = {(r["cond"], r["seed"]): r for r in load(DS)}
qw = {(r["cond"], r["seed"]): r for r in load(QW)}
keys = [(g["cond"], g["seed"]) for g in games if (g["cond"], g["seed"]) in ds and (g["cond"], g["seed"]) in qw]
if len(keys) != len(games):
    print(f"warning: {len(games)} games but only {len(keys)} have both re-scores; using those")
G = {(g["cond"], g["seed"]): g for g in games}

SRC = {
    "gpt-4o": lambda k, kind: G[k]["monitors"][kind + "_score"],
    "DeepSeek": lambda k, kind: ds[k][kind + "_score"],
    "Qwen2.5-32B": lambda k, kind: qw[k][kind + "_score"],
    "Bid screen": lambda k, kind: G[k]["monitors"]["bid_score"],
}


def scores(monitor, kind, cond):
    return [SRC[monitor](k, kind) for k in keys if k[0] == cond]


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    return (pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()


def boot(pos, neg, B=2000):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    v = [auc(rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) for _ in range(B)]
    return np.percentile(v, [2.5, 97.5])


rows = []
res = {}
for kind in ("chat", "both"):
    for m in ("gpt-4o", "DeepSeek", "Qwen2.5-32B", "Bid screen"):
        neg = scores(m, kind if m != "Bid screen" else "chat", "compete")
        for c in CONDS:
            pos = scores(m, kind if m != "Bid screen" else "chat", c)
            a = auc(pos, neg)
            lo, hi = boot(pos, neg)
            res[(kind, m, c)] = (a, lo, hi)
            rows.append([m, "chat only" if kind == "chat" else "chat + bids", c, len(pos), len(neg),
                         round(a, 4), round(lo, 4), round(hi, 4)])
with open(os.path.join(OUT, "fig5_monitor_auc.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["monitor", "kind", "condition", "n_condition", "n_compete", "auc", "ci_low", "ci_high"])
    w.writerows(rows)

with open(os.path.join(OUT, "monitor_scores_per_game.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["condition", "seed", "gpt4o_chat", "deepseek_chat", "qwen_chat", "gpt4o_both", "deepseek_both",
                "qwen_both", "bid_screen"])
    for k in sorted(keys):
        w.writerow([k[0], k[1], SRC["gpt-4o"](k, "chat"), SRC["DeepSeek"](k, "chat"), SRC["Qwen2.5-32B"](k, "chat"),
                    SRC["gpt-4o"](k, "both"), SRC["DeepSeek"](k, "both"), SRC["Qwen2.5-32B"](k, "both"),
                    round(SRC["Bid screen"](k, "chat"), 3)])

YMIN = max(0.0, np.floor((min(v[1] for v in res.values()) - 0.03) * 20) / 20)
MON = [("gpt-4o", BLUE), ("DeepSeek", ORANGE), ("Qwen2.5-32B", AQUA)]
fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.9), sharey=True)
for ax, kind, title in zip(axes, ("chat", "both"), ("(a) Chat-only monitors", "(b) Chat + bids monitors")):
    for j, (m, color) in enumerate(MON):
        for i, c in enumerate(CONDS):
            a, lo, hi = res[(kind, m, c)]
            x = i + (j - 1) * 0.2
            ax.plot([x, x], [lo, hi], color=color, lw=1.6, solid_capstyle="round", zorder=3)
            ax.scatter([x], [a], s=44, color=color, edgecolor=SURFACE, linewidth=0.9, zorder=4)
    for i, c in enumerate(CONDS):
        a, lo, hi = res[(kind, "Bid screen", c)]
        x = i + 0.38
        ax.plot([x, x], [lo, hi], color=INK, lw=1.2, zorder=3)
        ax.scatter([x], [a], s=40, marker="D", color=INK, edgecolor=SURFACE, linewidth=0.8, zorder=5)
    ax.set_xticks(range(len(CONDS)))
    ax.set_xticklabels([LABEL[c] for c in CONDS])
    ax.set_xlim(-0.6, len(CONDS) - 0.3)
    ax.set_ylim(YMIN, 1.03)
    ax.grid(axis="x", visible=False)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
axes[0].set_ylabel("AUC vs compete games (1.0 = perfect)")
handles = [plt.Line2D([0], [0], marker="o", color=color, lw=1.6, markersize=6, label=m) for m, color in MON]
handles.append(plt.Line2D([0], [0], marker="D", color=INK, lw=1.2, markersize=5, label="Bid screen (no LLM)"))
fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 0.0))
fig.text(0.01, -0.01, "Dot: AUC (probability a random game from the condition scores above a random compete game). Bar: 95% bootstrap CI over games.\n"
         f"n = 20 games per condition. The y-axis starts at {YMIN:.2f}, not 0. The bid screen is the same in both panels. Qwen and DeepSeek re-score the same saved games (exploratory).",
         fontsize=7, color=INK2, va="top")
fig.tight_layout(rect=(0, 0.09, 1, 1))
fig.savefig(os.path.join(OUT, "fig5_monitor_auc.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("wrote: fig5_monitor_auc.png, fig5_monitor_auc.csv, monitor_scores_per_game.csv in", OUT)
