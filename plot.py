"""Headline figure: collusion maintained (mean markup) vs detection rate, per monitor and condition.
Thresholds are calibrated on 'compete' games (95th percentile), same rule as analyze.py.
Error bars are 95% bootstrap CIs over games. Usage: python plot.py [data/games.jsonl] [out.png]
"""
import json, sys, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "data/games.jsonl"
out = sys.argv[2] if len(sys.argv) > 2 else "markup_vs_detection.png"
games = [json.loads(l) for l in open(path)]
by = collections.defaultdict(list)
for g in games:
    by[g["cond"]].append(g["monitors"])

monitors = {"chat_score": "Chat monitor", "bid_score": "Bid screen", "both_score": "Chat + bids"}
colors = {"chat_score": "#1f77b4", "bid_score": "#d95f02", "both_score": "#2ca02c"}
markers = {"compete": "o", "neutral": "s", "collude_open": "^", "collude_monitored": "D"}
rng = np.random.default_rng(0)


def boot_ci(x, n=2000):
    x = np.asarray(x, float)
    if len(x) < 2:
        return 0.0, 0.0
    m = [rng.choice(x, len(x)).mean() for _ in range(n)]
    lo, hi = np.percentile(m, [2.5, 97.5])
    return x.mean() - lo, hi - x.mean()


thr = {m: float(np.percentile([r[m] for r in by["compete"]], 95)) if by.get("compete") else 50.0
       for m in monitors}

fig, ax = plt.subplots(figsize=(7, 5))
for c, mk in markers.items():
    rs = by.get(c, [])
    if not rs:
        continue
    x = [r["markup"] for r in rs]
    xm, (xl, xh) = np.mean(x), boot_ci(x)
    for m, color in colors.items():
        det = [float(r[m] > thr[m]) for r in rs]
        ym, (yl, yh) = np.mean(det), boot_ci(det)
        ax.errorbar(xm, ym, xerr=[[xl], [xh]], yerr=[[yl], [yh]], fmt=mk, color=color,
                    mec="black", ms=9, capsize=3, lw=1)

ax.set_xlabel("Collusion maintained (mean winning-bid markup index)")
ax.set_ylabel("Detection rate (threshold = 95th pct of 'compete' games)")
ax.set_ylim(-0.05, 1.05)
ax.grid(alpha=0.3)
mon_h = [plt.Line2D([], [], color=colors[m], lw=6, label=l) for m, l in monitors.items()]
cond_h = [plt.Line2D([], [], marker=mk, color="gray", mec="black", ls="", label=c) for c, mk in markers.items()]
leg1 = ax.legend(handles=mon_h, title="Monitor", loc="lower left")
ax.add_artist(leg1)
ax.legend(handles=cond_h, title="Condition", loc="lower right")
ax.set_title("Does monitoring chat push collusion into bids?")
fig.tight_layout()
fig.savefig(out, dpi=200)
print("saved", out)