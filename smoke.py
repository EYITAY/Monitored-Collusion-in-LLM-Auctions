from llm import chat, ROLES

for role, spec in ROLES.items():
    try:
        out = chat(role, "You are a test.", 'Reply with exactly: {"bid": 12}', max_tokens=30)
        print(f"OK    {role:<9} {spec:<35} -> {out.strip()[:60]!r}")
    except Exception as e:
        print(f"FAIL  {role:<9} {spec:<35} -> {type(e).__name__}: {str(e)[:150]}")
