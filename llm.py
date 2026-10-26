"""One client for OpenAI, DeepSeek and Gemini (all expose OpenAI-compatible APIs).

Put settings in a file named exactly `.env` next to this file, one KEY=value per line:
  OPENAI_API_KEY=...
  DEEPSEEK_API_KEY=...
  GEMINI_API_KEY=...
  BIDDER_1=deepseek:<model id>
  BIDDER_2=gemini:<model id>
  BIDDER_3=openai:<model id>
  MONITOR=openai:<model id>
Run `python models.py` to list the model ids each key can use.
Set MOCK=1 to run with no API calls (random bids, canned chat) for testing.
"""
import os, random, json, time
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Look next to this file (not the shell's cwd); .env wins over stale shell variables.
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
except ImportError:
    pass  # fine if you export variables in the shell instead

PROVIDERS = {
    "openai": dict(base_url=None, key="OPENAI_API_KEY"),
    "deepseek": dict(base_url="https://api.deepseek.com", key="DEEPSEEK_API_KEY"),
    "gemini": dict(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", key="GEMINI_API_KEY"),
    "modal": dict(base_url=os.getenv("MODAL_BASE_URL"), key="MODAL_API_KEY"),
}

# Defaults are placeholders: set exact model ids in .env.
ROLES = {
    "bidder_1": os.getenv("BIDDER_1", "deepseek:deepseek-chat").strip(),
    "bidder_2": os.getenv("BIDDER_2", "gemini:gemini-2.0-flash").strip(),
    "bidder_3": os.getenv("BIDDER_3", "openai:gpt-4o-mini").strip(),
    # Monitor: strong model. Note self-preference risk if it shares a family with a bidder.
    "monitor": os.getenv("MONITOR", "openai:gpt-4o").strip(),
}

_clients = {}

# Running tally of API usage per role, written to the run manifest by run.py (cost accounting).
# Token counts are whatever the provider reports; for reasoning models they may include hidden thinking.
import threading
_lock = threading.Lock()
USAGE = {r: dict(calls=0, retries=0, empty_replies=0, prompt_tokens=0, completion_tokens=0) for r in ROLES}


def _tally(role, **kw):
    with _lock:
        for k, v in kw.items():
            USAGE[role][k] += v


def usage_snapshot():
    with _lock:
        return json.loads(json.dumps(USAGE))


def get_key(provider):
    var = PROVIDERS[provider]["key"]
    key = (os.getenv(var) or "").strip().strip('"').strip("'")
    if not key:
        raise RuntimeError(f"{var} is not set. Add it to .env next to llm.py (KEY=value, no quotes needed).")
    return key


def _client(provider):
    if provider not in _clients:
        from openai import OpenAI
        _clients[provider] = OpenAI(api_key=get_key(provider), base_url=PROVIDERS[provider]["base_url"])
    return _clients[provider]


def _split(spec):
    provider, model = spec.split(":", 1)
    model = model.strip()
    if model.startswith("models/"):  # Gemini lists ids as models/<id>
        model = model[len("models/"):]
    return provider.strip(), model


def chat(role, system, user, temperature=1.0, max_tokens=400, retries=4):
    if os.getenv("MOCK"):
        _tally(role, calls=1)
        return _mock(role, user)
    provider, model = _split(ROLES[role])
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    # Gemini 3.x spends tokens on hidden thinking, so tiny limits give empty replies.
    if provider == "gemini":
        max_tokens = max(max_tokens * 8, 1024)
    kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    for i in range(retries):
        try:
            r = _client(provider).chat.completions.create(**kwargs)
            text = r.choices[0].message.content or ""
            u = getattr(r, "usage", None)
            _tally(role, calls=1,
                   prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
                   completion_tokens=getattr(u, "completion_tokens", 0) or 0)
            if not text.strip() and i < retries - 1:  # empty reply: give it more room and retry
                _tally(role, empty_replies=1)
                if "max_tokens" in kwargs:
                    kwargs["max_tokens"] *= 2
                elif "max_completion_tokens" in kwargs:
                    kwargs["max_completion_tokens"] *= 2
                continue
            return text
        except Exception as e:
            msg = str(e)
            _tally(role, retries=1)
            # Some newer models reject max_tokens / temperature: adapt once, then retry.
            if "max_completion_tokens" in msg and "max_tokens" in kwargs:
                kwargs["max_completion_tokens"] = kwargs.pop("max_tokens") * 4  # headroom for reasoning
                continue
            if "temperature" in msg and "temperature" in kwargs:
                kwargs.pop("temperature")
                continue
            # A DAILY quota (e.g. Gemini free tier: 20 requests/day/model) or no credit will not fix itself
            # within a run: fail fast. Per-minute rate limits are retried with a longer backoff.
            if type(e).__name__ == "RateLimitError":
                if "PerDay" in msg or "insufficient_quota" in msg:
                    raise RuntimeError(f"{role} ({ROLES[role]}): daily quota or credit exhausted "
                                       f"(enable billing or switch this role to another provider): {msg[:200]}") from None
                if i < retries - 1:
                    time.sleep(10 * (i + 1))
                    continue
            # Auth/model-name errors will not fix themselves: fail fast with a clear message.
            if type(e).__name__ in ("AuthenticationError", "NotFoundError", "PermissionDeniedError"):
                raise RuntimeError(f"{role} ({ROLES[role]}): {type(e).__name__}: {msg[:200]}") from None
            if i == retries - 1:
                raise
            time.sleep(2 ** i)


def _mock(role, user):
    if role == "monitor":
        return json.dumps({"score": random.randint(0, 100), "reason": "mock"})
    if "BID NOW" in user:
        return json.dumps({"bid": round(random.uniform(10, 30), 1)})
    return random.choice(["Let's keep prices stable.", "I will bid competitively.", "Good round."])