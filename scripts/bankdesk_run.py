"""Run a model through BankDesk episodes and score them (R1 outcome, R2 process).

Backends:
  vllm:PATH_OR_ID      batched, all live episodes advance one turn per generate call (greedy)
  bedrock:MODEL_ID     e.g. bedrock:us.openai.gpt-6-luna (reference / teacher), threaded
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


def run_vllm(model, cases, system, max_tokens, tokenizer=None):
    from vllm import LLM, SamplingParams
    llm = LLM(model=model, tokenizer=tokenizer or model, dtype="bfloat16", max_model_len=4096, gpu_memory_utilization=0.85,
              seed=0, enable_prefix_caching=True)
    sp = SamplingParams(temperature=0.0, max_tokens=max_tokens)
    eps = [bd.Episode(c) for c in cases]
    for turn in range(bd.MAX_ACTIONS):
        live = [e for e in eps if not e.done]
        if not live: break
        outs = llm.chat([bd.messages(e, system) for e in live], sp, use_tqdm=False)
        for e, o in zip(live, outs): e.step(o.outputs[0].text)
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
    eps = [bd.Episode(c) for c in cases]
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
    a = ap.parse_args()
    system = bd.SYSTEM_PROMPT + (bd.STRONG_PROMPT_ADDON if a.system == "strong" else "")
    cases = load_cases(a.cards, a.split, a.limit, tuple(a.langs.split(",")))
    print(f"{len(cases)} episodes ({a.split})", flush=True)
    kind, model = a.backend.split(":", 1)
    t = time.time()
    eps = run_vllm(model, cases, system, a.max_tokens, a.tokenizer) if kind == "vllm" else run_bedrock(model, cases, system, a.max_tokens)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    recs = []
    with open(a.out, "w", encoding="utf-8") as f:
        for e in eps:
            r = e.record() | {"model": a.tag, "system": a.system}; recs.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = summarize(recs); print_table(rows, f"{a.tag} ({a.system} prompt, {time.time() - t:.0f}s)")
    if a.summary_out: json.dump({"tag": a.tag, "system": a.system, "rows": rows}, open(a.summary_out, "w"), indent=1)
    sys.stdout.flush()
    if kind == "vllm": os._exit(0)
