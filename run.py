"""Usage: python run.py --conds compete neutral collude_open collude_monitored --seeds 20 --rounds 20
Writes one JSON line per game to data/games.jsonl (resumable: skips finished cond/seed pairs).
Start with --seeds 2 --rounds 5 to check cost before scaling up.

Documentation outputs (for the technical report / blog post):
  - every game line carries `meta` (models, prompts, params, timestamps) and `code_version`
  - <out dir>/run_manifest.jsonl gets one line per invocation: command, args, resolved model ids,
    package versions, SHA-256 of every source file, API usage (calls / tokens / retries), wall time.
"""
import argparse, hashlib, json, os, platform, sys, time, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from game import play, CONDITIONS
from monitors import run_all
from llm import ROLES, usage_snapshot

HERE = Path(__file__).resolve().parent


def code_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in sorted(HERE.glob("*.py"))}


def versions():
    v = {"python": platform.python_version(), "platform": platform.platform()}
    for pkg in ("openai", "numpy", "matplotlib", "python-dotenv"):
        try:
            from importlib.metadata import version
            v[pkg] = version(pkg)
        except Exception:
            v[pkg] = None
    return v


ap = argparse.ArgumentParser()
ap.add_argument("--conds", nargs="+", default=CONDITIONS)
ap.add_argument("--seeds", type=int, default=20)
ap.add_argument("--rounds", type=int, default=20)
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--out", default="data/games.jsonl")
a = ap.parse_args()

out_dir = os.path.dirname(a.out) or "."
os.makedirs(out_dir, exist_ok=True)
done = set()
if os.path.exists(a.out):
    for line in open(a.out):
        g = json.loads(line)
        done.add((g["cond"], g["seed"]))

jobs = [(c, s) for c in a.conds for s in range(a.seeds) if (c, s) not in done]
hashes = code_hashes()
code_version = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]


def work(job):
    c, s = job
    g = play(c, s, a.rounds)
    g["monitors"] = run_all(g)
    g["code_version"] = code_version
    return g


t0 = time.time()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
n_done = 0
with ThreadPoolExecutor(a.workers) as ex, open(a.out, "a") as f:
    for g in ex.map(work, jobs):
        f.write(json.dumps(g) + "\n")
        f.flush()
        n_done += 1
        print(g["cond"], g["seed"], round(g["monitors"]["markup"], 3))

manifest = {
    "started_at": started,
    "wall_seconds": round(time.time() - t0, 1),
    "argv": sys.argv,
    "args": vars(a),
    "mock": bool(os.getenv("MOCK")),
    "games_skipped_already_done": len(done),
    "games_written": n_done,
    "models": dict(ROLES),
    "code_version": code_version,
    "code_sha256_12": hashes,
    "versions": versions(),
    "usage": usage_snapshot(),
}
with open(os.path.join(out_dir, "run_manifest.jsonl"), "a") as mf:
    mf.write(json.dumps(manifest) + "\n")
u = manifest["usage"]
print(f"\nDone: {n_done} games in {manifest['wall_seconds']}s (code {code_version}). API usage this run:")
for role, d in u.items():
    print(f"  {role:<9} {ROLES[role]:<32} calls={d['calls']:<5} in={d['prompt_tokens']:<8} out={d['completion_tokens']:<8} "
          f"retries={d['retries']} empty={d['empty_replies']}")