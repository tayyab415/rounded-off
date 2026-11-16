"""Run an agent through BankDesk v4 worlds and print a summary. Design: notes/BANKDESK_V4_DESIGN.md.

  python3 scripts/bankdesk_v4_run.py --backend reference --prefix pilot --n 48 --out runs/bankdesk_v4/pilot/reference.jsonl
  python3 scripts/bankdesk_v4_run.py --backend nebius:zai-org/GLM-5.3-Flash --prefix pilot --n 48 --out runs/.../GLM.jsonl
  python3 scripts/bankdesk_v4_run.py --backend hf:tyb343/rounded-off-bankdesk-grpo-v3 --prefix pilot --n 48 --out ...
Backends: reference | fixed | hold | pay (scripted), nebius:MODEL (API, no GPU), hf:REPO or hf:REPO+ADAPTER_DIR (transformers on a GPU).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk_v4 as g
import bankdesk_v4_env as e

STOP = ["\nCustomer", "\n[Check]", "\n[Form]", "\n[Policy]", "\n[Error]", "\nBank:", "\nACTION", "\n  a reply"]


def run_scripted(worlds, agent, words): return [e.run(w, agent, words=words.get(w["id"])) for w in worlds]


def run_nebius(model, worlds, max_tokens, words, threads=8):
    from concurrent.futures import ThreadPoolExecutor
    from nebius_client import chat

    def play(w):
        ep = e.Episode(w, words=words.get(w["id"]))
        while not ep.done: ep.step(chat(model, e.messages(ep), max_tokens=max_tokens, tag="bankdesk_v4"))
        return ep
    with ThreadPoolExecutor(threads) as ex: return list(ex.map(play, worlds))


def run_hf(repo, worlds, max_tokens, words, batch=16, sample=False, temperature=1.0):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    repo, _, adapter = repo.partition("+")       # hf:BASE or hf:BASE+ADAPTER_DIR (a LoRA adapter from bankdesk_v4_train.py)
    tok = AutoTokenizer.from_pretrained(repo); tok.padding_side = "left"
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    dtype = torch.bfloat16 if torch.cuda.get_device_capability(0)[0] >= 8 else torch.float16      # T4: real fp16, not emulated bf16
    model = AutoModelForCausalLM.from_pretrained(repo, dtype=dtype, device_map={"": 0})
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    model.eval()
    eps = [e.Episode(w, words=words.get(w["id"])) for w in worlds]
    gen = dict(do_sample=True, temperature=temperature, top_p=1.0) if sample else dict(do_sample=False)
    while True:
        live = [ep for ep in eps if not ep.done]
        if not live: break
        for i in range(0, len(live), batch):
            chunk = live[i:i + batch]
            prompts = [tok.apply_chat_template(e.messages(ep), tokenize=False, add_generation_prompt=True) for ep in chunk]
            enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=max_tokens, stop_strings=STOP, tokenizer=tok, **gen)
            for ep, row in zip(chunk, out):
                ep.step(tok.decode(row[enc["input_ids"].shape[1]:], skip_special_tokens=True))
        print(f"  {sum(ep.done for ep in eps)}/{len(eps)} done", flush=True)
    return eps


def summarize(recs):
    import numpy as np
    sc = [r for r in recs if r["truth"] == "scam"]; ge = [r for r in recs if r["truth"] == "genuine"]
    forms = [r for r in recs if r["form_sent"]]
    tried = sum(any(t["tool"] == "request_details" or "request_details" in (t["raw"] or "") for t in r["turns"]) for r in recs)
    pct = lambda xs: round(100 * float(np.mean(xs)), 1) if len(xs) else None
    return {"episodes": len(recs), "reward": round(float(np.mean([r["reward"] for r in recs])), 3),
            "utility": round(float(np.mean([r["utility"] for r in recs])), 3),
            "decided_pct": pct([r["end"] == "decided" for r in recs]), "rejected_per_episode": round(float(np.mean([r["rejected"] for r in recs])), 2),
            "secret_asked": sum(r["secret_asked"] for r in recs), "scams_paid_pct": pct([bool(r["scam_paid"]) for r in sc]),
            "genuine_paid_pct": pct([bool(r["genuine_paid"]) for r in ge]), "genuine_held_pct": pct([bool(r["genuine_held"]) for r in ge]),
            "form_sent_pct": pct([r["form_sent"] for r in recs]), "form_attempted": tried, "form_parsed": len(forms),
            "fields_per_form": round(float(np.mean([r["n_fields"] for r in forms])), 2) if forms else None,
            "lookups_per_episode": round(float(np.mean([r["n_lookups"] for r in recs])), 2),
            "risk_stated_vs_exact": round(float(np.mean([abs(e.RISK[r["risk"]] - r["p_scam_at_decision"]) for r in recs if r["risk"]])), 3)
            if any(r["risk"] for r in recs) else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True); ap.add_argument("--prefix", default="pilot"); ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--out", required=True); ap.add_argument("--max-tokens", type=int, default=220); ap.add_argument("--tag")
    ap.add_argument("--words", help="wording rows (bankdesk_v4_words.py); worlds without a row use the English template")
    ap.add_argument("--only-with-words", action="store_true"); ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--sample", action="store_true", help="sample at --temperature instead of greedy (DAgger roll-outs)")
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--regime", default="base", choices=["base", "shift"], help="shift: the held-out test regime (RULE V4-8)")
    a = ap.parse_args()
    if a.regime != "base": g.set_regime(a.regime)
    words = {json.loads(l)["id"]: json.loads(l) for l in open(a.words, encoding="utf-8")} if a.words else {}
    ids = [f"{a.prefix}-{i}" for i in range(a.start, a.start + a.n)]
    if a.only_with_words: ids = [i for i in ids if i in words]
    worlds = [g.sample_world(i) for i in ids]
    kind, _, name = a.backend.partition(":")
    if kind == "nebius": eps = run_nebius(name, worlds, a.max_tokens, words)
    elif kind == "hf": eps = run_hf(name, worlds, a.max_tokens, words, sample=a.sample, temperature=a.temperature)
    else: eps = run_scripted(worlds, {"reference": e.reference_step, "fixed": e.agent_fixed_form, "hold": e.agent_always("hold", "very_high"),
                                      "pay": e.agent_always("pay", "low")}[kind], words)
    tag = a.tag or (name.split("/")[-1] if name else kind)
    recs = [ep.record() | {"agent": tag, "generator": g.params_hash(), "regime": g.REGIME, "worded": ep.world["id"] in words} for ep in eps]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    s = summarize(recs); json.dump(s | {"agent": tag, "generator": g.params_hash()}, open(a.out.replace(".jsonl", ".summary.json"), "w"), indent=1)
    print(tag, json.dumps(s))
