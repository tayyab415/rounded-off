"""GRPO in BankDesk, single-decision form (TRL GRPOTrainer, LoRA), started from the SFT checkpoint.

Training states are the decision points of the teacher's kept train trajectories (before each agent turn). For a state,
the model samples one action; the reward function rebuilds the episode in the simulator, replays the earlier actions,
applies the sampled action, then finishes the episode with the scripted label-aware policy (escalate a scam, complete
a genuine task) and returns rubric R1 of the finished episode. So the sampled action is judged by where it leads:
an unsafe change in a scam case is -1 whatever follows; escalating a genuine customer is -0.5; a rejected action
costs 0.1; asking when the budget is nearly spent leads to running out of actions (0).
This is RL inside the environment with a verifiable reward, but credit is assigned one decision at a time, not over
whole sampled episodes; the write-up says so.
Gates (notes/SOL_REVIEW.md): a smoke run first (--max-steps 20); continue only if enough groups have reward variance.
Usage (GPU): python bankdesk_grpo.py --base /tmp/bankdesk_sft --demos data/bankdesk/sft_train.jsonl --out /tmp/grpo \
               [--max-steps 20] [--push REPO]
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd
from bankdesk_run import load_cases


def build_states(demos_path, cards_path, split):
    cases = {c.case_id: c for c in load_cases(cards_path, split)}
    rows = []
    for line in open(demos_path, encoding="utf-8"):
        r = json.loads(line)
        if r["case_id"] not in cases: continue
        prior = []
        for i, m in enumerate(r["messages"]):
            if m["role"] != "assistant": continue
            rows.append({"prompt": r["messages"][:i], "case_id": r["case_id"], "prior": json.dumps(prior, ensure_ascii=False),
                         "variant": r["variant"], "clarity": r["clarity"], "lang": r["lang"]})
            prior.append(m["content"])
    return rows, cases


def make_reward(cases):
    def reward(prompts, completions, case_id, prior, **kw):
        out = []
        for comp, cid, pr in zip(completions, case_id, prior):
            text = comp[0]["content"] if isinstance(comp, list) else comp
            ep = bd.Episode(cases[cid])
            for act in json.loads(pr):
                if not ep.done: ep.step(act)
            if not ep.done: ep.step(text)
            while not ep.done: ep.step(bd.policy_oracle(ep))
            out.append(ep.outcome()["reward"])
        return out
    return reward


def make_cfg(cls, **kw):
    """Build a TRL config, dropping settings the installed version does not know (TRL changes them between releases)."""
    import dataclasses
    known = {f.name for f in dataclasses.fields(cls)}
    dropped = sorted(set(kw) - known)
    if dropped: print("config: dropped unknown settings", dropped, flush=True)
    return cls(**{k: v for k, v in kw.items() if k in known})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--demos", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--cards", default="data/bankdesk/cards.jsonl"); ap.add_argument("--max-steps", type=int, default=150)
    ap.add_argument("--lr", type=float, default=2e-5); ap.add_argument("--beta", type=float, default=0.02)
    ap.add_argument("--gens", type=int, default=4); ap.add_argument("--prompts-per-step", type=int, default=8)
    ap.add_argument("--push"); ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer
    t0 = time.time()
    rows, cases = build_states(a.demos, a.cards, "train")
    print(f"{len(rows)} decision states from {len({r['case_id'] for r in rows})} train cases", flush=True)
    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16)
    cfg = make_cfg(GRPOConfig, output_dir=a.out + "_ckpt", learning_rate=a.lr, beta=a.beta, num_generations=a.gens,
                     per_device_train_batch_size=a.gens * a.prompts_per_step, gradient_accumulation_steps=1,
                     max_completion_length=96, temperature=1.0, max_steps=a.max_steps, logging_steps=1, bf16=True,
                     gradient_checkpointing=True, save_strategy="no", report_to="none", seed=a.seed)
    peft = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules="all-linear", task_type="CAUSAL_LM")
    tr = GRPOTrainer(model=model, reward_funcs=[make_reward(cases)], args=cfg, train_dataset=Dataset.from_list(rows).shuffle(seed=a.seed),
                     processing_class=tok, peft_config=peft)
    tr.train()
    log = tr.state.log_history
    zero_std = [x.get("frac_reward_zero_std") for x in log if "frac_reward_zero_std" in x]
    gate = {"steps": len(zero_std), "mean_frac_groups_with_variance": (1 - sum(zero_std) / len(zero_std)) if zero_std else None,
            "first_reward": next((x.get("reward") for x in log if "reward" in x), None),
            "last_reward": next((x.get("reward") for x in reversed(log) if "reward" in x), None)}
    print("GATE", json.dumps(gate), flush=True)
    merged = tr.model.merge_and_unload()
    merged.save_pretrained(a.out, safe_serialization=True); tok.save_pretrained(a.out)
    json.dump({"base": a.base, "states": len(rows), "max_steps": a.max_steps, "lr": a.lr, "beta": a.beta, "gens": a.gens,
               "prompts_per_step": a.prompts_per_step, "seed": a.seed, "train_secs": round(time.time() - t0), "gate": gate, "log": log},
              open(os.path.join(a.out, "train_info.json"), "w"), indent=1)
    print(f"TRAINED in {time.time() - t0:.0f}s -> {a.out}", flush=True)
    if a.push:
        from huggingface_hub import HfApi
        HfApi().create_repo(a.push, private=True, exist_ok=True)
        HfApi().upload_folder(folder_path=a.out, repo_id=a.push, commit_message="BankDesk GRPO (LoRA merged)")
        print("pushed", a.push, flush=True)
