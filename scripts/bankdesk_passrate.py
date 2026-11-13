"""Pass-rate filter for GRPO (DAPO-style dynamic sampling done offline; TRL has no online dynamic sampling).

For every candidate decision state (opening of each card case, and the states after [verify_payee] and
[verify_payee, check_session]), sample N actions from the policy with vLLM, score each with the GRPO reward (replay,
apply the action, scripted label-aware finish, rubric R1, repeat cost), and keep only states whose N rewards are not
all equal. Groups with identical rewards carry no GRPO gradient, which is why three smoke runs found no signal.
Usage (GPU): python bankdesk_passrate.py --model PATH --cards data/bankdesk/cards_rl.jsonl --split rl --n 8 \
               --out states.jsonl --stats stats.json
"""
import argparse, collections, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd
from bankdesk_run import load_cases
from bankdesk_grpo import make_reward

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True); ap.add_argument("--tokenizer", default="CohereLabs/tiny-aya-global")
ap.add_argument("--cards", default="data/bankdesk/cards_rl.jsonl"); ap.add_argument("--split", default="rl")
ap.add_argument("--n", type=int, default=8); ap.add_argument("--temperature", type=float, default=1.0)
ap.add_argument("--out", required=True); ap.add_argument("--stats", required=True)
a = ap.parse_args()
t0 = time.time()
cases = {c.case_id: c for c in load_cases(a.cards, a.split)}
states = []
for cid, c in cases.items():
    v = f"ACTION: verify_payee(account={c.payee_account})"
    for prefix in ([], [v], [v, "ACTION: check_session()"]):
        ep = bd.Episode(c)
        for act in prefix: ep.step(act)
        if ep.done: continue
        states.append({"prompt": bd.messages(ep), "case_id": cid, "prior": json.dumps(prefix), "variant": c.variant,
                       "clarity": c.clarity, "lang": c.lang, "stage": ["opening", "after_verify", "after_checks"][len(prefix)]})
from vllm import LLM, SamplingParams
llm = LLM(model=a.model, tokenizer=a.tokenizer, dtype="bfloat16", max_model_len=4096, gpu_memory_utilization=0.85, seed=0,
          enable_prefix_caching=True)
outs = llm.chat([s["prompt"] for s in states], SamplingParams(n=a.n, temperature=a.temperature, max_tokens=96, stop=bd.STOP), use_tqdm=False)
reward = make_reward(cases, a.n)
keep, stats = [], collections.Counter()
for s, o in zip(states, outs):
    texts = [x.text for x in o.outputs]
    rs = reward([None] * len(texts), [[{"content": t}] for t in texts], [s["case_id"]] * len(texts), [s["prior"]] * len(texts))
    mixed = len(set(rs)) > 1
    key = (s["variant"], s["stage"])
    stats[key + ("n",)] += 1; stats[key + ("mixed",)] += int(mixed); stats[key + ("mean_reward_x1000",)] += int(1000 * sum(rs) / len(rs))
    if mixed: keep.append(dict(s, rewards=rs))
with open(a.out, "w", encoding="utf-8") as f:
    for s in keep: f.write(json.dumps(s, ensure_ascii=False) + "\n")
summary = {f"{v}/{st}": {"states": stats[(v, st, "n")], "mixed": stats[(v, st, "mixed")],
                          "mean_reward": round(stats[(v, st, "mean_reward_x1000")] / 1000 / max(1, stats[(v, st, "n")]), 3)}
           for v in ("scam", "genuine") for st in ("opening", "after_verify", "after_checks")}
summary["total"] = {"states": len(states), "kept_mixed": len(keep), "secs": round(time.time() - t0)}
json.dump(summary, open(a.stats, "w"), indent=1); print(json.dumps(summary, indent=1), flush=True)
sys.stdout.flush(); os._exit(0)
