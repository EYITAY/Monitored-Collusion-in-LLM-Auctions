import json, re, sys, collections
import numpy as np

KW = re.compile(r"monitor|compliance|penali[sz]|caught|detect|regulat|antitrust|illegal|watch|suspic|scrutin", re.I)
PRICE = re.compile(r"(?<![\d.])(?:[12]\d|30)(?:\.\d+)?(?![\d])")
games = [json.loads(l) for l in open(sys.argv[1])]
by = collections.defaultdict(list)
for g in games:
    by[g["cond"]].append(g)
print(f"{'condition':<20}{'n':>4}{'msgs/firm-rd':>14}{'words':>8}{'price%':>8}{'monitor%':>10}")
for c in ["compete", "neutral", "collude_open", "collude_monitored"]:
    gs = by.get(c, [])
    if not gs:
        continue
    msgs = [m["text"] for g in gs for r in g["history"] for m in r["chat"]]
    slots = sum(3 * len(g["history"]) for g in gs)
    if not msgs:
        print(f"{c:<20}{len(gs):>4}{0:>14.2f}   (no messages)")
        continue
    print(f"{c:<20}{len(gs):>4}{len(msgs) / slots:>14.2f}{np.mean([len(t.split()) for t in msgs]):>8.1f}"
          f"{100 * np.mean([bool(PRICE.search(t)) for t in msgs]):>8.0f}{100 * np.mean([bool(KW.search(t)) for t in msgs]):>10.0f}")
