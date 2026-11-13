"""Pilot: does Tiny Aya Global (unmodified, via HF Inference / Cohere provider) protect a user who is mid-scam?
Greedy-ish (temperature 0), no system prompt, same as our eval. Usage: python3 run_pilot.py prompts.jsonl out.jsonl"""
import json, os, sys, urllib.request
src, out = sys.argv[1], sys.argv[2]
tok = os.environ["HF_TOKEN"]
with open(out, "w") as f:
    for r in map(json.loads, open(src)):
        body = {"model": "CohereLabs/tiny-aya-global:cohere", "messages": [{"role": "user", "content": r["prompt"]}],
                "temperature": 0, "max_tokens": 256}
        req = urllib.request.Request("https://router.huggingface.co/v1/chat/completions", json.dumps(body).encode(),
                                     {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        try: r["response"] = json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]["content"]
        except Exception as e: r["response"] = f"ERROR {e}"
        f.write(json.dumps(r, ensure_ascii=False) + "\n"); print(r["id"], r["response"][:80].replace("\n", " "))
