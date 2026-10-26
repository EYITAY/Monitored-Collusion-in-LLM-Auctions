"""Re-score SAVED games with a different monitor model (no games are replayed).

Usage: python rescore.py --games data/pilot.jsonl --monitor deepseek:deepseek-chat
Writes data/pilot.rescore_<provider>_<model>.jsonl (override with --out). Resumable.

Only the two LLM monitors are re-run (chat-only, chat+bids). The bid screen is deterministic, so it is
not repeated. Same prompts and settings as monitors.py; only the model changes. Use compare.py afterwards.
"""
import argparse, json, os, re, time, datetime
from concurrent.futures import ThreadPoolExecutor
import llm
from llm import ROLES, usage_snapshot
from monitors import chat_monitor, both_monitor, bid_features, MONITOR_TEMPERATURE, MONITOR_MAX_TOKENS

ap = argparse.ArgumentParser()
ap.add_argument("--games", required=True)
ap.add_argument("--monitor", required=True, help='"provider:model", e.g. deepseek:deepseek-chat')
ap.add_argument("--out")
ap.add_argument("--workers", type=int, default=4)
a = ap.parse_args()

ROLES["monitor"] = a.monitor  # monitors.py calls chat("monitor", ...), so this swaps the model
tag = re.sub(r"[^A-Za-z0-9]+", "_", a.monitor).strip("_")
out = a.out or a.games.replace(".jsonl", f".rescore_{tag}.jsonl")

games = [json.loads(l) for l in open(a.games)]
done = set()
if os.path.exists(out):
    done = {(json.loads(l)["cond"], json.loads(l)["seed"]) for l in open(out)}
todo = [g for g in games if (g["cond"], g["seed"]) not in done]


def work(g):
    cs, cr, cok, craw = chat_monitor(g)
    bs, br, bok, braw = both_monitor(g)
    return {"cond": g["cond"], "seed": g["seed"], "monitor_model": a.monitor,
            "monitor_temperature": MONITOR_TEMPERATURE, "monitor_max_tokens": MONITOR_MAX_TOKENS,
            "chat_score": cs, "both_score": bs, "chat_reason": cr, "both_reason": br,
            "chat_parse_ok": cok, "both_parse_ok": bok, "chat_raw": craw, "both_raw": braw,
            "scored_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_games": os.path.basename(a.games), "source_code_version": g.get("code_version")}


t0 = time.time()
with ThreadPoolExecutor(a.workers) as ex, open(out, "a") as f:
    for r in ex.map(work, todo):
        f.write(json.dumps(r) + "\n"); f.flush()
        print(r["cond"], r["seed"], "chat", r["chat_score"], "both", r["both_score"])
u = usage_snapshot()["monitor"]
print(f"\nRescored {len(todo)} games with {a.monitor} in {time.time() - t0:.1f}s -> {out}")
print(f"  monitor calls={u['calls']} in={u['prompt_tokens']} out={u['completion_tokens']} retries={u['retries']} empty={u['empty_replies']}")