import os
from openai import OpenAI
from llm import PROVIDERS

for name, cfg in PROVIDERS.items():
    key = os.getenv(cfg["key"])
    if not key:
        print(f"\n{name}: no key set"); continue
    try:
        ids = sorted(m.id for m in OpenAI(api_key=key, base_url=cfg["base_url"]).models.list())
        print(f"\n{name}:"); print("\n".join("  " + i for i in ids))
    except Exception as e:
        print(f"\n{name}: FAIL {type(e).__name__}: {str(e)[:120]}")
