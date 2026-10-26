"""Threshold-free comparison of monitors: AUC of each score separating a condition from 'compete'.
AUC = probability that a random game from the condition scores higher than a random 'compete' game
(ties count half). 0.5 = no discrimination, 1.0 = perfect. 95% bootstrap CIs over games.
Usage: python auc.py data/main.jsonl [data/main.rescore_deepseek_deepseek_chat.jsonl]
A = scores stored in the games file; B = the rescore file (chat and both monitors only).
"""
import json, sys, collections
import numpy as np

games = [json.loads(l) for l in open(sys.argv[1])]
resc = [json.loads(l) for l in open(sys.argv[2])] if len(sys.argv) > 2 else []
rng = np.random.default_rng(0)
cols = [("A chat", games, "chat_score", True), ("A bid", games, "bid_score", True), ("A both", games, "both_score", True)]
if resc:
    cols += [("B chat", resc, "chat_score", False), ("B both", resc, "both_score", False)]


def scores(rows, key, stored):
    d = collections.defaultdict(list)
    for r in rows:
        d[r["cond"]].append((r["monitors"] if stored else r)[key])
    return d


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    return (pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()


def boot(pos, neg, B=2000):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    v = [auc(rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) for _ in range(B)]
    return np.percentile(v, [2.5, 97.5])


S = {name: scores(rows, key, stored) for name, rows, key, stored in cols}
print("AUC for separating each condition from 'compete' [95% bootstrap CI]")
print(f"{'condition':<20}" + "".join(f"{name:<22}" for name, *_ in cols))
for c in ["neutral", "collude_open", "collude_monitored"]:
    cells = []
    for name, *_ in cols:
        pos, neg = S[name][c], S[name]["compete"]
        lo, hi = boot(pos, neg)
        cells.append(f"{auc(pos, neg):.2f} [{lo:.2f},{hi:.2f}]".ljust(22))
    print(f"{c:<20}" + "".join(cells))
print("\nMean score per condition (to see where each monitor puts competitive games):")
print(f"{'condition':<20}" + "".join(f"{name:<10}" for name, *_ in cols))
for c in ["compete", "neutral", "collude_open", "collude_monitored"]:
    print(f"{c:<20}" + "".join(f"{np.mean(S[name][c]):<10.1f}" for name, *_ in cols))