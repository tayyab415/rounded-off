"""BankDesk v4: GRPO, one decision at a time, after the DAgger rounds. Design: notes/BANKDESK_V4_DESIGN.md s.15.

States are the decision points of episodes a student played on GRPO worlds (rl-250..499 by default, never used for
SFT or DAgger). For a state the model samples G actions. Each is scored by code with the exact value of the case after
that action, with the reference policy playing the rest (bankdesk_v4_env.score_decision): no luck from the hidden
story or from which answers came back. A reply that cannot be parsed scores the state's value minus PARSE_FAIL.

Judge, tie-break only (Tayyab's decision 2026-11-16): within a group, the samples whose code reward is within TIE of
the group's best and that end the case with a message are ranked by one batched DeepSeek-V4.1-Flash call on the
customer message alone (it never sees the action, the records or the outcome). The best-ranked gets +JUDGE_BONUS,
the others less. The bonus is far below any code-reward gap that matters, so the judge cannot outvote the outcome.
The judge runs only with --judge and a Nebius key (AWS); without it the reward is code only.

Pass-rate filter (keep states whose G samples differ): `states` mode samples G actions per state with the SFT model
and keeps states whose rewards spread by more than --min-spread.

  python bankdesk_v4_grpo.py states --runs r2.rl250-499.jsonl --words words_rl.jsonl --out grpo_states.jsonl
  python bankdesk_v4_grpo.py train --base BASE --adapter r2/adapter --states grpo_states.jsonl --out /tmp/v4_grpo [--judge]
"""
import argparse, hashlib, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk_v4 as g
import bankdesk_v4_env as e

PARSE_FAIL, TIE, JUDGE_BONUS = 0.5, 0.01, 0.02
JUDGE_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
JUDGE_SYSTEM = """You compare short messages that a bank's payments assistant sent to a customer at the end of a case.
Rank them from best to worst for the customer. A good message:
- is in the same language and script as the customer would expect (English, Hindi in Devanagari, or Hinglish in Latin script, as given);
- says plainly what the bank did (paid, delayed, or stopped the payment) and why, naming specific facts rather than vague words;
- tells the customer what happens next and what they can do, including calling 1930 or reporting at cybercrime.gov.in when a payment was stopped for fraud;
- is polite and does not blame or shame the customer;
- never asks for an OTP, PIN, password or card number, and never tells the customer how to get round a hold;
- is short; padding, repetition and filler make it worse;
- a message that is empty, cut off, or not addressed to the customer is the worst.
Judge only the message text. You are not told the facts of the case, so do not reward claims you cannot check; reward clarity, specificity of form, and the rules above.
Reply with JSON only: {"ranking": [ids from best to worst]}. Include every id exactly once.
Examples of the scale (not to be ranked): "We have stopped this payment of Rs 40,000 because the account was opened two days ago and many strangers paid into it today. Please do not send money or share any OTP. Our team will call your registered number; you can also call 1930." is better than "Payment not allowed due to risk." which is better than "ok"."""


# ---------------------------------------------------------------- states
def episode_states(rec, words):
    """Decision states of one played episode: (world id, prior actions) before each reply the student wrote."""
    out, prior = [], []
    for t in rec["turns"]:
        out.append({"id": rec["id"], "prior": list(prior)}); prior.append(t["raw"])
    return out


def state_prompt(st, words):
    ep = e.Episode(g.sample_world(st["id"]), words=words.get(st["id"]))
    for a in st["prior"]: ep.step(a)
    return None if ep.done else e.messages(ep)


def reward_of(st, text, words, cache={}):
    key = (st["id"], tuple(st["prior"]), text)
    if key not in cache:
        world = g.sample_world(st["id"]); w = words.get(st["id"])
        if e.parse(text)[0] is None:                     # unparseable: lose a turn and pay PARSE_FAIL
            ep = e.Episode(world, words=w)
            for a in st["prior"]: ep.step(a)
            base = e.state_value(ep.ctx, ep.lookups)[0] if ep.fields is None else e.best_decision(ep.weights(), ep.ctx["stake"], ep.fields, bool(ep.contradicted()))[0]
            cache[key] = (base - g.LOOKUP_COST * len(ep.lookups) - PARSE_FAIL, {"kind": None, "ok": False})
        else:
            cache[key] = e.score_decision(world, st["prior"], text, words=w)
    return cache[key]


# ---------------------------------------------------------------- judge (tie-break)
JUDGE_CACHE = {}


def judge_rank(messages, lang):
    """Ranks for a list of messages, best first, from one DeepSeek call. Returns a list of positions or None."""
    from nebius_client import chat
    key = hashlib.sha256(json.dumps([lang, messages], ensure_ascii=False).encode()).hexdigest()
    if key in JUDGE_CACHE: return JUDGE_CACHE[key]
    items = "\n".join(f"id {i}: {m}" for i, m in enumerate(messages))
    try:
        txt = chat(JUDGE_MODEL, [{"role": "system", "content": JUDGE_SYSTEM},
                                 {"role": "user", "content": f"Customer's language: {lang}.\n{items}"}], max_tokens=60, tag="v4_grpo_judge")
        rk = [int(x) for x in json.loads(re.search(r"\{.*\}", txt, re.S).group(0))["ranking"]]
        rk = rk if sorted(rk) == list(range(len(messages))) else None
    except Exception as ex:
        print("judge failed:", str(ex)[:120], flush=True); rk = None
    JUDGE_CACHE[key] = rk
    return rk


def message_of(text):
    tool, args, err = e.parse(text)
    return args.get("message", "").strip() if tool == "decide" and not err else None


STATS = {"groups": 0, "groups_varied": 0, "parse_fail": 0, "samples": 0, "judge_groups": 0, "judge_failed": 0, "judge_abs_share": []}


def make_reward(words, gens, use_judge):
    def reward(prompts, completions, sid, lang, **kw):
        texts = [c[0]["content"] if isinstance(c, list) else c for c in completions]
        states = [STATE_BY_ID[s] for s in sid]
        code = [reward_of(st, t, words)[0] for st, t in zip(states, texts)]
        bonus = [0.0] * len(code)
        STATS["samples"] += len(code); STATS["parse_fail"] += sum(e.parse(t)[0] is None for t in texts)
        for i in range(0, len(code) - gens + 1, gens):
            grp = code[i:i + gens]; STATS["groups"] += 1; STATS["groups_varied"] += (max(grp) - min(grp)) > 1e-6
            if not use_judge: continue
            top = [j for j in range(i, i + gens) if code[j] >= max(grp) - TIE and message_of(texts[j])]
            msgs = [message_of(texts[j]) for j in top]
            if len(top) < 2 or len(set(msgs)) < 2: continue
            STATS["judge_groups"] += 1
            rk = judge_rank(msgs, lang[i])
            if rk is None: STATS["judge_failed"] += 1; continue
            for place, pos in enumerate(rk): bonus[top[pos]] = JUDGE_BONUS * (1 - place / (len(rk) - 1))
            spread = max(grp) - min(grp)
            STATS["judge_abs_share"].append(JUDGE_BONUS / (spread + JUDGE_BONUS))
        return [c + b for c, b in zip(code, bonus)]
    return reward


STATE_BY_ID = {}


def make_cfg(cls, **kw):
    import dataclasses
    known = {f.name for f in dataclasses.fields(cls)}
    dropped = sorted(set(kw) - known)
    if dropped: print("config: dropped unknown settings", dropped, flush=True)
    return cls(**{k: v for k, v in kw.items() if k in known})


def load_policy(base, adapter):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16 if bf16 else torch.float16)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    return tok, model, bf16


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("states"); s1.add_argument("--runs", required=True, nargs="+"); s1.add_argument("--words")
    s1.add_argument("--out", required=True); s1.add_argument("--base"); s1.add_argument("--adapter")
    s1.add_argument("--samples", type=int, default=8); s1.add_argument("--min-spread", type=float, default=0.02)
    s1.add_argument("--max-states", type=int, default=3000)
    s2 = sub.add_parser("train"); s2.add_argument("--base", required=True); s2.add_argument("--adapter"); s2.add_argument("--states", required=True)
    s2.add_argument("--words"); s2.add_argument("--out", required=True); s2.add_argument("--max-steps", type=int, default=150)
    s2.add_argument("--lr", type=float, default=1e-5); s2.add_argument("--gens", type=int, default=8); s2.add_argument("--prompts-per-step", type=int, default=4)
    s2.add_argument("--temperature", type=float, default=1.0); s2.add_argument("--epsilon-high", type=float, default=0.28)
    s2.add_argument("--max-completion", type=int, default=200); s2.add_argument("--judge", action="store_true"); s2.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    words = {json.loads(l)["id"]: json.loads(l) for l in open(a.words, encoding="utf-8")} if a.words else {}

    if a.cmd == "states":
        states = [st for path in a.runs for rec in map(json.loads, open(path, encoding="utf-8")) for st in episode_states(rec, words)]
        states = states[:a.max_states]; print(f"{len(states)} decision states", flush=True)
        if a.base:      # pass-rate filter: sample with the policy, keep states whose rewards spread
            import torch
            tok, model, _ = load_policy(a.base, a.adapter); model = model.cuda().eval(); tok.padding_side = "left"
            if tok.pad_token is None: tok.pad_token = tok.eos_token
            kept = []
            for k, st in enumerate(states):
                msgs = state_prompt(st, words)
                if msgs is None: continue
                p = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                enc = tok([p] * a.samples, return_tensors="pt", add_special_tokens=False).to(model.device)
                with torch.no_grad():
                    out = model.generate(**enc, max_new_tokens=200, do_sample=True, temperature=1.0, stop_strings=["\nACTION", "\n[", "\nCustomer"], tokenizer=tok)
                texts = [tok.decode(r[enc["input_ids"].shape[1]:], skip_special_tokens=True) for r in out]
                rs = [reward_of(st, t, words)[0] for t in texts]
                st["spread"] = max(rs) - min(rs); st["mean"] = sum(rs) / len(rs)
                if st["spread"] > a.min_spread: kept.append(st)
                if k % 50 == 0: print(f"  {k}/{len(states)} states, kept {len(kept)}", flush=True)
            print(f"pass-rate filter: kept {len(kept)} of {len(states)} states (spread > {a.min_spread})", flush=True); states = kept
        with open(a.out, "w", encoding="utf-8") as f:
            for st in states: f.write(json.dumps(st, ensure_ascii=False) + "\n")
        sys.exit(0)

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from trl import GRPOConfig, GRPOTrainer
    t0 = time.time()
    states = [json.loads(l) for l in open(a.states, encoding="utf-8")]
    rows = []
    for i, st in enumerate(states):
        msgs = state_prompt(st, words)
        if msgs is None: continue
        sid = f"s{i}"; STATE_BY_ID[sid] = st
        rows.append({"prompt": msgs, "sid": sid, "lang": (words.get(st["id"]) or {}).get("lang", "en")})
    print(f"{len(rows)} GRPO states", flush=True)
    tok, model, bf16 = load_policy(a.base, a.adapter)
    cfg = make_cfg(GRPOConfig, output_dir=a.out + "_ckpt", learning_rate=a.lr, beta=0.0, num_generations=a.gens,
                   per_device_train_batch_size=a.gens * a.prompts_per_step, gradient_accumulation_steps=1, max_completion_length=a.max_completion,
                   temperature=a.temperature, epsilon_high=a.epsilon_high, loss_type="dapo", max_steps=a.max_steps, logging_steps=1,
                   bf16=bf16, fp16=not bf16, gradient_checkpointing=True, save_strategy="no", report_to="none", seed=a.seed)
    peft = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules="all-linear", task_type="CAUSAL_LM")
    tr = GRPOTrainer(model=model, reward_funcs=[make_reward(words, a.gens, a.judge)], args=cfg,
                     train_dataset=Dataset.from_list(rows).shuffle(seed=a.seed), processing_class=tok, peft_config=peft)
    tr.train()
    os.makedirs(a.out, exist_ok=True)
    tr.model.save_pretrained(os.path.join(a.out, "adapter")); tok.save_pretrained(os.path.join(a.out, "adapter"))
    merged = tr.model.merge_and_unload()      # SFT and GRPO changes in one checkpoint, for roll-outs and rounding
    merged.save_pretrained(os.path.join(a.out, "merged"), safe_serialization=True); tok.save_pretrained(os.path.join(a.out, "merged"))
    share = STATS.pop("judge_abs_share")
    stats = dict(STATS, judge_bonus_share_of_spread_mean=(sum(share) / len(share)) if share else None)
    json.dump({"base": a.base, "sft_adapter": a.adapter, "states": len(rows), "max_steps": a.max_steps, "lr": a.lr, "gens": a.gens,
               "judge": a.judge, "train_secs": round(time.time() - t0), "stats": stats, "log": tr.state.log_history},
              open(os.path.join(a.out, "train_info.json"), "w"), indent=1, default=str)
    print("STATS", json.dumps(stats), flush=True); print(f"TRAINED in {time.time() - t0:.0f}s -> {a.out}", flush=True)
