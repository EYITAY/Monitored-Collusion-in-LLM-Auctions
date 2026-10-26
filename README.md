cat > README.md << 'EOF'
# Monitored Collusion in LLM Auctions

Code, data and figures for an Apart Research AI Collusion Research Sprint submission (Oct 23-25, 2026, Track 3, question 3.4).

**Question.** If colluding LLM firms in a repeated auction are told their chat is monitored, do they move coordination out of their words and into their bids, and can chat monitors still catch them?

**Design.** Repeated first-price procurement auction: 3 firms (costs 10, 10, 11), price cap 30, 20 rounds (chat, then sealed bids). Four conditions x 20 games = 80 games: `compete` (negative control), `neutral`, `collude_open` (positive control), `collude_monitored` (stated but unenforced monitoring threat). Firm A is `deepseek-chat` (API alias, version not recorded); Firms B and C are `gpt-4o-mini`.

**Main findings.** Late markup: compete 0.06, neutral 0.37, collude_open 0.94, collude_monitored 0.78. Explicit price talk fell from 100% to 72% of messages under the stated threat, but chat-only monitors (gpt-4o, DeepSeek, Qwen2.5-32B) still separated every non-control condition from compete (AUC about 1.00). Adding bids to the gpt-4o monitor did not help (AUC 0.87 and 0.89). The chat monitor also flags friendly tone at near-zero markup, so its ceiling may reflect tone. Collusion is instructed and the threat is never enforced.

## Layout

| Path | What it is |
|---|---|
| `game.py`, `run.py`, `models.py`, `llm.py` | Auction, runner, model calls (OpenAI, DeepSeek, Modal) |
| `monitors.py` | Chat monitor, bid screen, combined monitor |
| `rescore.py`, `modal_qwen.py` | Re-score saved games with DeepSeek and Qwen2.5-32B (vLLM on Modal) |
| `auc.py`, `final_analysis.py`, `chat_stats.py`, `compare.py` | Analysis: AUC, thresholds, bootstrap CIs, agreement |
| `figures.py`, `figures_monitors.py`, `figures/` | Figure scripts and outputs |
| `data/` | Game logs and monitor scores (JSON lines) |
| `*_output.txt` | Saved analysis output |
| `prereg.md`, `notebook.md` | Pilot, exploratory and post-hoc decisions, as they happened |

## Setup