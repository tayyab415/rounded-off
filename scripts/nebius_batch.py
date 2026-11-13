"""Batched, cache-friendly labelling on Nebius (Tayyab's idea, 2026-11-13).

Instead of one call per item, each call carries one long FIXED system prompt (rubric + worked examples, kept above
~1,100 tokens so the provider caches it) and a batch of numbered items; the model returns one JSON object
{"1": "A", "2": "C", ...}. Measured: DeepSeek-V4.1-Flash caches a repeated prefix of >= ~1,000 tokens (cached input
$0.006/M vs $0.30/M); GLM-5.3-Flash from ~450 tokens ($0.03 vs $0.15). Items missing from a reply are re-asked one by one.
Spend is logged to notes/nebius_spend.jsonl with cached tokens priced as cached, and counts against nebius_client.CAP.
Batching can change labels (items see each other), so every rubric is re-checked against hand labels before use.

  from nebius_batch import label_batch
  labels = label_batch(model, system_prompt, items, render, allowed={"A","B","C","D"}, batch=20)
"""
import json, os, random, re, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nebius_client as nc

CACHED = {"deepseek-ai/DeepSeek-V4.1-Flash-1017": 0.006, "zai-org/GLM-5.3-Flash": 0.03}
_lock = threading.Lock()
STATS = {"calls": 0, "prompt": 0, "cached": 0, "out": 0, "usd": 0.0}


def _post(model, messages, max_tokens, tag):
    pin, pout = nc.PRICES[model]
    worst = sum(len(m["content"]) for m in messages) / 2.5 * pin / 1e6 + (max_tokens + 64) * pout / 1e6
    with _lock:
        if nc.spent() + worst > nc.CAP: raise RuntimeError(f"Nebius cap ${nc.CAP} would be exceeded")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.0, **nc.EXTRA.get(model, {})}
    req = urllib.request.Request(nc.URL, json.dumps(body).encode(), {"Authorization": f"Bearer {nc._key()}", "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=300)); break
        except urllib.error.HTTPError as e:
            if e.code == 402: raise RuntimeError("Nebius balance exhausted (402)")
            if attempt == 5 or e.code in (400, 401, 403, 404): raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 5: raise
        time.sleep(2 ** attempt + random.random())
    u = d.get("usage", {}); p = u.get("prompt_tokens", 0); o = u.get("completion_tokens", 0)
    c = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or u.get("prompt_cache_hit_tokens") or 0
    usd = (p - c) * pin / 1e6 + c * CACHED.get(model, pin) / 1e6 + o * pout / 1e6
    with _lock:
        nc.spent(); nc._spent += usd
        with open(nc.LEDGER, "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "tag": tag, "in": p, "cached": c,
                                "out": o, "usd": round(usd, 6)}) + "\n")
        for k, v in (("calls", 1), ("prompt", p), ("cached", c), ("out", o), ("usd", usd)): STATS[k] += v
    return d["choices"][0]["message"].get("content") or ""


def _parse(text, n, allowed):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    m = re.search(r"\{.*\}", text, re.S)
    out = {}
    if m:
        try:
            for k, v in json.loads(m.group(0)).items():
                v = str(v).strip().upper()[:1]
                if str(k).strip().isdigit() and v in allowed: out[int(k)] = v
        except json.JSONDecodeError:
            pass
    if not out:   # fallback: lines like "3: B"
        for k, v in re.findall(r"(\d+)\s*[:=)\-]\s*\"?([A-Z])", text):
            if v in allowed: out[int(k)] = v
    return {k: v for k, v in out.items() if 1 <= k <= n}


def label_batch(model, system, items, render, allowed, batch=20, threads=6, tag="batch"):
    """items: list of dicts; render(item) -> text of one item. Returns a list of labels (None if unparseable)."""
    groups = [items[i:i + batch] for i in range(0, len(items), batch)]

    def run(group):
        user = "\n\n".join(f"### Item {j + 1}\n{render(it)}" for j, it in enumerate(group))
        user += (f"\n\nGrade each of the {len(group)} items independently. Reply with ONLY a JSON object mapping item "
                 f"number to one letter, for example {{\"1\": \"A\", \"2\": \"C\"}}.")
        got = _parse(_post(model, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                           max_tokens=8 * len(group) + 40, tag=tag), len(group), allowed)
        labels = []
        for j, it in enumerate(group):
            if j + 1 in got: labels.append(got[j + 1]); continue
            one = _parse(_post(model, [{"role": "system", "content": system},
                                       {"role": "user", "content": f"### Item 1\n{render(it)}\n\nReply with ONLY {{\"1\": \"<letter>\"}}."}],
                               max_tokens=20, tag=tag + "-retry"), 1, allowed)
            labels.append(one.get(1))
        return labels
    if not groups: return []
    first = run(groups[0])                      # warm the cache with one call before going parallel
    with ThreadPoolExecutor(threads) as ex: rest = list(ex.map(run, groups[1:]))
    return first + [l for g in rest for l in g]
