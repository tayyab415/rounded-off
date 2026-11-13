"""Run a model through BankDesk episodes and score them (R1 outcome, R2 process).

Backends:
  vllm:PATH_OR_ID      batched, all live episodes advance one turn per generate call (greedy)
  bedrock:MODEL_ID     e.g. bedrock:us.openai.gpt-6-luna (no longer used: see PLAN.md 2026-11-13 ~19:40)
  nebius:MODEL_ID      e.g. nebius:deepseek-ai/DeepSeek-V4.1-Flash-1017 (open-weight reference), threaded, $15 cap
Usage:
  python bankdesk_run.py --backend vllm:CohereLabs/tiny-aya-global --cards data/bankdesk/cards.jsonl --split test \
      --system default --tag M0 --out runs/bankdesk/M0.default.jsonl
  --system strong adds the anti-scam rules (prompt-only control). --limit N for smoke tests.
Prints a summary table; --summary-out writes it as JSON.
"""
import argparse, collections, json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd


def load_cases(cards_path, split, limit=None, langs=("en", "hi")):
    cases = []
    for line in open(cards_path, encoding="utf-8"):
        r = json.loads(line)
        if r["lang"] not in langs or (split != "all" and r["split"] != split): continue
        cases += bd.cases_from_card(r["card"], r["card_id"], r["lang"])
    if limit:
        keep = sorted({c.card_id for c in cases})[:limit]
        cases = [c for c in cases if c.card_id in keep]
    return cases


CUSTOMER = None   # set from --customer: None = scripted (bankdesk.scripted_customer), else bankdesk_customer.llm_customer


def run_vllm(model, cases, system, max_tokens, tokenizer=None):
    from vllm import LLM, SamplingParams
    llm = LLM(model=model, tokenizer=tokenizer or model, dtype="bfloat16", max_model_len=4096, gpu_memory_utilization=0.85,
              seed=0, enable_prefix_caching=True)
    sp = SamplingParams(temperature=0.0, max_tokens=max_tokens, stop=bd.STOP)
    eps = [bd.Episode(c, CUSTOMER) for c in cases]
    for turn in range(bd.MAX_ACTIONS):
        live = [e for e in eps if not e.done]
        if not live: break
        outs = llm.chat([bd.messages(e, system) for e in live], sp, use_tqdm=False)
        from concurrent.futures import ThreadPoolExecutor      # LLM-customer replies are network calls: run them in parallel
        with ThreadPoolExecutor(16) as ex: list(ex.map(lambda eo: eo[0].step(eo[1].outputs[0].text), zip(live, outs)))
        print(f"turn {turn + 1}: {len(live)} live", flush=True)
    return eps


def run_bedrock(model_id, cases, system, max_tokens, threads=8):
    import boto3
    from concurrent.futures import ThreadPoolExecutor
    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    def call(msgs):
        conv = [{"role": m["role"], "content": [{"text": m["content"]}]} for m in msgs if m["role"] != "system"]
        for attempt in range(6):
            try:
                r = client.converse(modelId=model_id, system=[{"text": msgs[0]["content"]}], messages=conv,
                                    inferenceConfig={"maxTokens": max_tokens},
                                    additionalModelRequestFields={"reasoning": {"effort": "none"}})
                return "".join(b.get("text", "") for b in r["output"]["message"]["content"])
            except Exception as ex:
                if attempt == 5: return f"[backend error] {ex}"
                time.sleep(2 ** attempt + random.random())

    def play(e):
        while not e.done: e.step(call(bd.messages(e, system)))
        return e
    eps = [bd.Episode(c, CUSTOMER) for c in cases]
    with ThreadPoolExecutor(threads) as ex: return list(ex.map(play, eps))


def run_nebius(model, cases, system, max_tokens, threads=8):
    from concurrent.futures import ThreadPoolExecutor
    from nebius_client import chat

    def play(e):
        while not e.done:
            try: e.step(chat(model, bd.messages(e, system), max_tokens=max_tokens, tag="bankdesk"))
            except RuntimeError as ex: print("stopped:", ex, flush=True); raise
        return e
    eps = [bd.Episode(c, CUSTOMER) for c in cases]
    with ThreadPoolExecutor(threads) as ex: return list(ex.map(play, eps))


def run_hfrouter(model, cases, system, max_tokens, threads=6):
    """HF Inference Providers (OpenAI-compatible router), for cheap observation of Tiny Aya Global (M0) only."""
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    tok = os.environ["HF_TOKEN"]

    def call(msgs):
        body = {"model": model, "messages": msgs, "temperature": 0, "max_tokens": max_tokens}   # provider mangles stop strings
        for attempt in range(5):
            try:
                req = urllib.request.Request("https://router.huggingface.co/v1/chat/completions", json.dumps(body).encode(),
                                             {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
                return json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]["content"] or ""
            except Exception as ex:
                if attempt == 4: return f"[backend error] {ex}"
                time.sleep(2 ** attempt)

    def play(e):
        while not e.done: e.step(call(bd.messages(e, system)))
        return e
    eps = [bd.Episode(c, CUSTOMER) for c in cases]
    with ThreadPoolExecutor(threads) as ex: return list(ex.map(play, eps))


def summarize(records):
    groups = collections.defaultdict(list)
    for r in records:
        for key in (("all", r["lang"]), (f"{r['variant']}-{r['clarity']}", r["lang"]), (r["variant"], r["lang"])):
            groups[key].append(r)
    rows = []
    for (g, lang), rs in sorted(groups.items()):
        scam = [r for r in rs if r["variant"] == "scam"]; gen = [r for r in rs if r["variant"] == "genuine"]
        row = {"group": g, "lang": lang, "n": len(rs), "mean_reward": sum(r["reward"] for r in rs) / len(rs),
               "rejected_per_ep": sum(r["rejected"] for r in rs) / len(rs),
               "asked_before_change": sum(r["asked_before_change"] for r in rs) / len(rs)}
        if scam: row["unsafe"] = sum(r["unsafe"] for r in scam) / len(scam); row["escalated_scam"] = sum(r["end"] == "escalated" and not r["unsafe"] for r in scam) / len(scam)
        if gen: row["completed"] = sum(r["completed"] for r in gen) / len(gen); row["false_escalation"] = sum(r["false_escalation"] for r in gen) / len(gen)
        rows.append(row)
    return rows


def print_table(rows, tag):
    print(f"\nBankDesk {tag}")
    print(f"{'group':<20}{'lang':<5}{'n':>5}{'reward':>8}{'unsafe':>8}{'escal.':>8}{'done':>8}{'false-esc':>10}{'rej/ep':>8}{'asked':>7}")
    pct = lambda r, k: f"{100 * r[k]:7.1f}%" if k in r else f"{'-':>8}"
    for r in rows:
        print(f"{r['group']:<20}{r['lang']:<5}{r['n']:>5}{r['mean_reward']:>8.2f}{pct(r, 'unsafe')}{pct(r, 'escalated_scam')}"
              f"{pct(r, 'completed')}{pct(r, 'false_escalation'):>10}{r['rejected_per_ep']:>8.2f}{100 * r['asked_before_change']:6.0f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True); ap.add_argument("--cards", required=True); ap.add_argument("--split", default="test")
    ap.add_argument("--system", choices=["default", "strong"], default="default"); ap.add_argument("--tag", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--summary-out"); ap.add_argument("--limit", type=int)
    ap.add_argument("--max-tokens", type=int, default=160); ap.add_argument("--tokenizer"); ap.add_argument("--langs", default="en,hi")
    ap.add_argument("--customer", choices=["scripted", "llm"], default="scripted"); ap.add_argument("--cases")
    a = ap.parse_args()
    if a.customer == "llm":
        from bankdesk_customer import llm_customer
        CUSTOMER = llm_customer
    system = bd.SYSTEM_PROMPT + (bd.STRONG_PROMPT_ADDON if a.system == "strong" else "")
    cases = load_cases(a.cards, a.split, a.limit, tuple(a.langs.split(",")))
    if a.cases: keep = set(open(a.cases).read().split()); cases = [c for c in cases if c.case_id in keep]
    print(f"{len(cases)} episodes ({a.split})", flush=True)
    kind, model = a.backend.split(":", 1)
    t = time.time()
    run = {"vllm": lambda: run_vllm(model, cases, system, a.max_tokens, a.tokenizer),
           "bedrock": lambda: run_bedrock(model, cases, system, a.max_tokens),
           "nebius": lambda: run_nebius(model, cases, system, a.max_tokens),
           "hfrouter": lambda: run_hfrouter(model, cases, system, a.max_tokens)}[kind]
    eps = run()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    recs = []
    with open(a.out, "w", encoding="utf-8") as f:
        for e in eps:
            r = e.record() | {"model": a.tag, "system": a.system, "customer": a.customer}; recs.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = summarize(recs); print_table(rows, f"{a.tag} ({a.system} prompt, {time.time() - t:.0f}s)")
    if a.summary_out: json.dump({"tag": a.tag, "system": a.system, "rows": rows}, open(a.summary_out, "w"), indent=1)
    sys.stdout.flush()
    if kind == "vllm": os._exit(0)
