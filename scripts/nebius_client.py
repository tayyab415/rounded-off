"""Nebius Token Factory client with a hard spending cap (Tayyab's balance is $30; our cap is $15).

Nebius has no balance API, so spend is computed from each response's `usage` x the public price list
(tokenfactory.nebius.com/api/public/models_info, read 2026-11-13) and appended to notes/nebius_spend.jsonl.
Before every call the worst case (prompt estimate + max_tokens) must fit under the cap, or the call raises.
Thinking is switched off (DeepSeek) or kept low (GLM, which cannot switch it off), since hidden reasoning is billed.
Only protective / evaluation content goes here (scam victims, genuine customers, simulator turns), never requests for
help with fraud (see memory: no harmful content to closed or third-party APIs).

  from nebius_client import chat, spent
  text = chat("deepseek-ai/DeepSeek-V4.1-Flash-1017", messages, max_tokens=200)
  python scripts/nebius_client.py status
"""
import json, os, random, threading, time, urllib.error, urllib.request

CAP = 15.00
URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"
PRICES = {  # USD per 1M tokens (input, output)
    "deepseek-ai/DeepSeek-V4.1-Flash-1017": (0.30, 1.20),
    "zai-org/GLM-5.3-Flash": (0.15, 0.50),
    "Qwen/Qwen3-30B-A3B-Instruct-2507": (0.10, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
    "google/gemma-3-27b-it": (0.10, 0.30),
}
EXTRA = {"deepseek-ai/DeepSeek-V4.1-Flash-1017": {"reasoning_effort": "none"},
         "zai-org/GLM-5.3-Flash": {"reasoning_effort": "low"}}
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "notes", "nebius_spend.jsonl")
_lock = threading.Lock()
_spent = None


def _key():
    k = os.environ.get("NEBIUS_API_KEY")
    if k: return k
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    for l in open(env):
        if l.startswith("NEBIUS_API_KEY="): return l.split("=", 1)[1].strip()
    raise RuntimeError("NEBIUS_API_KEY not set")


def spent():
    global _spent
    if _spent is None:
        _spent = sum(json.loads(l)["usd"] for l in open(LEDGER)) if os.path.exists(LEDGER) else 0.0
    return _spent


def _record(model, usage, tag):
    global _spent
    pin, pout = PRICES[model]
    usd = usage.get("prompt_tokens", 0) * pin / 1e6 + usage.get("completion_tokens", 0) * pout / 1e6
    with _lock:
        spent(); _spent += usd
        with open(LEDGER, "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "tag": tag,
                                "in": usage.get("prompt_tokens", 0), "out": usage.get("completion_tokens", 0), "usd": round(usd, 6)}) + "\n")
    return usd


def chat(model, messages, max_tokens=256, temperature=0.0, tag="", retries=6):
    if model not in PRICES: raise ValueError(f"no price for {model}; add it to PRICES first")
    pin, pout = PRICES[model]
    est_in = sum(len(m["content"]) for m in messages) / 2.5          # chars per token is >= 2.5 for EN and HI here
    worst = est_in * pin / 1e6 + (max_tokens + 64) * pout / 1e6
    with _lock:
        if spent() + worst > CAP: raise RuntimeError(f"Nebius cap: spent ${spent():.2f}, this call could reach ${spent() + worst:.2f} > ${CAP}")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, **EXTRA.get(model, {})}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=180))
            _record(model, d.get("usage", {}), tag)
            return d["choices"][0]["message"].get("content") or ""
        except urllib.error.HTTPError as e:
            if e.code == 402: raise RuntimeError("Nebius balance exhausted (402)")
            if attempt == retries - 1 or e.code in (400, 401, 403, 404): raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1: raise
        time.sleep(2 ** attempt + random.random())


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(LEDGER)] if os.path.exists(LEDGER) else []
    by = {}
    for r in rows: by.setdefault(r["model"], [0, 0.0]); by[r["model"]][0] += 1; by[r["model"]][1] += r["usd"]
    for m, (n, usd) in by.items(): print(f"{m:<40} {n:>6} calls  ${usd:.3f}")
    print(f"spent ${spent():.3f} of cap ${CAP:.2f} (balance $30; the 6 test calls on 2026-11-13 ~19:50 IST cost < $0.001)")
