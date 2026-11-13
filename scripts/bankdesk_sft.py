"""SFT warm start in BankDesk: LoRA on Tiny Aya from teacher trajectories (scripts/bankdesk_teacher.py), then merge.

Each kept trajectory becomes one example per agent turn: prompt = the conversation so far (student's default system
prompt, account summary, customer messages, tool results), completion = the teacher's action for that turn. Loss is
on the completion only, so the model learns actions, not the simulator's text.
Usage (GPU): python bankdesk_sft.py --base tyb343/rounded-off-tiny-aya-bank-sft --train data/bankdesk/sft_train.jsonl \
                 --out /tmp/bankdesk_sft [--push tyb343/rounded-off-bankdesk-sft]
"""
import argparse, json, os, sys, time
import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer


def turn_examples(path):
    out = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line); msgs = r["messages"]
        for i, m in enumerate(msgs):
            if m["role"] == "assistant":
                out.append({"prompt": msgs[:i], "completion": [m]})
    return out


def make_cfg(cls, **kw):
    """Build a TRL config, dropping settings the installed version does not know (TRL changes them between releases)."""
    import dataclasses
    known = {f.name for f in dataclasses.fields(cls)}
    dropped = sorted(set(kw) - known)
    if dropped: print("config: dropped unknown settings", dropped, flush=True)
    return cls(**{k: v for k, v in kw.items() if k in known})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--train", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--push"); ap.add_argument("--epochs", type=float, default=2); ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16); ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    t0 = time.time()
    ex = turn_examples(a.train)
    print(f"{len(ex)} turn examples from {a.train}", flush=True)
    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16)
    cfg = make_cfg(SFTConfig, output_dir=a.out + "_ckpt", num_train_epochs=a.epochs, learning_rate=a.lr, per_device_train_batch_size=4,
                    gradient_accumulation_steps=2, max_length=2048, bf16=True, logging_steps=10, save_strategy="no",
                    report_to="none", seed=a.seed, lr_scheduler_type="cosine", warmup_steps=10, gradient_checkpointing=True)
    peft = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
    tr = SFTTrainer(model=model, args=cfg, train_dataset=Dataset.from_list(ex), processing_class=tok, peft_config=peft)
    tr.train()
    merged = tr.model.merge_and_unload()
    merged.save_pretrained(a.out, safe_serialization=True); tok.save_pretrained(a.out)
    json.dump({"base": a.base, "train": a.train, "turn_examples": len(ex), "epochs": a.epochs, "lr": a.lr, "lora_rank": a.rank,
               "seed": a.seed, "train_secs": round(time.time() - t0), "log": tr.state.log_history},
              open(os.path.join(a.out, "train_info.json"), "w"), indent=1)
    print(f"TRAINED in {time.time() - t0:.0f}s -> {a.out}", flush=True)
    if a.push:
        from huggingface_hub import HfApi
        HfApi().create_repo(a.push, private=True, exist_ok=True)
        HfApi().upload_folder(folder_path=a.out, repo_id=a.push, commit_message="BankDesk SFT (LoRA merged)")
        print("pushed", a.push, flush=True)
