"""BankDesk v4: LoRA fine-tune of Tiny Aya on per-step rows from bankdesk_v4_data.py. Design: notes/BANKDESK_V4_DESIGN.md s.15.

Each row is one decision: the chat so far and one target action. Loss is on the target only. Earlier agent turns in a
row are history (in DAgger rows they are the student's own, possibly wrong, actions) and are never trained on.
Light by default: one epoch. A deeper fine-tune makes the policy too sure of itself and leaves GRPO nothing to learn
from (arXiv 2606.18487; and v3, where 83% of states gave one reward).

  python bankdesk_v4_train.py --base tyb343/rounded-off-tiny-aya-bank-sft-wiseft --train sft_r0.jsonl --out /tmp/v4_r0
  add --max-steps 60 for a speed probe; --merge to also save merged weights (about 7 GB).
"""
import argparse, json, os, time
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")      # one GPU: two would wrap the model in DataParallel
import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer


def examples(paths):
    out = []
    for path in paths:
        for line in open(path, encoding="utf-8"):
            m = json.loads(line)["messages"]
            assert m[-1]["role"] == "assistant"
            out.append({"prompt": m[:-1], "completion": [m[-1]]})
    return out


def make_cfg(cls, **kw):
    import dataclasses
    known = {f.name for f in dataclasses.fields(cls)}
    dropped = sorted(set(kw) - known)
    if dropped: print("config: dropped unknown settings", dropped, flush=True)
    return cls(**{k: v for k, v in kw.items() if k in known})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--train", required=True, nargs="+"); ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=1); ap.add_argument("--lr", type=float, default=1e-4); ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--seed", type=int, default=13); ap.add_argument("--bs", type=int, default=2); ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--max-steps", type=int, default=-1); ap.add_argument("--max-length", type=int, default=1536); ap.add_argument("--merge", action="store_true")
    a = ap.parse_args(); t0 = time.time()
    ex = examples(a.train); print(f"{len(ex)} decision rows from {a.train}", flush=True)
    bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8      # T4 and P100 report bf16 "supported" via emulation, then fail in training
    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16 if bf16 else torch.float16)
    cfg = make_cfg(SFTConfig, output_dir=a.out + "_ckpt", num_train_epochs=a.epochs, max_steps=a.max_steps, learning_rate=a.lr,
                   per_device_train_batch_size=a.bs, gradient_accumulation_steps=a.accum, max_length=a.max_length, bf16=bf16, fp16=not bf16,
                   logging_steps=5, save_strategy="no", report_to="none", seed=a.seed, lr_scheduler_type="cosine", warmup_steps=10,
                   gradient_checkpointing=True)
    peft = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
    tr = SFTTrainer(model=model, args=cfg, train_dataset=Dataset.from_list(ex), processing_class=tok, peft_config=peft)
    t1 = time.time(); tr.train(); steps = tr.state.global_step
    os.makedirs(a.out, exist_ok=True)
    tr.model.save_pretrained(os.path.join(a.out, "adapter")); tok.save_pretrained(os.path.join(a.out, "adapter"))
    info = {"base": a.base, "train": a.train, "rows": len(ex), "epochs": a.epochs, "steps": steps, "lr": a.lr, "lora_rank": a.rank, "seed": a.seed,
            "bs": a.bs, "accum": a.accum, "max_length": a.max_length, "train_secs": round(time.time() - t1), "secs_per_step": round((time.time() - t1) / max(1, steps), 2),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "dtype": "bf16" if bf16 else "fp16", "log": tr.state.log_history}
    json.dump(info, open(os.path.join(a.out, "train_info.json"), "w"), indent=1)
    print(f"TRAINED {steps} steps in {info['train_secs']}s ({info['secs_per_step']} s/step) on {info['gpu']} -> {a.out}", flush=True)
    if a.merge:
        merged = tr.model.merge_and_unload(); merged.save_pretrained(os.path.join(a.out, "merged"), safe_serialization=True)
        tok.save_pretrained(os.path.join(a.out, "merged")); print("merged weights saved", flush=True)
