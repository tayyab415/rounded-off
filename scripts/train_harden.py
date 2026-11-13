"""Fine-tune Tiny Aya on bank data with SafeTune: PlainSFT (drift) or SafeGrad (hardened).

Usage: python train_harden.py --method plainsft|safegrad --data SFT.jsonl --out DIR
       [--safety REFUSALS.jsonl] [--epochs 2] [--lr 1e-4] [--bs 4] [--seed 13] [--max-len 1024] [--rho 0.1] [--limit N]
Output: a merged full checkpoint (SafeTune saves LoRA merged) with lexsi_provenance.json.
"""
import argparse, json, os, time
import safetune
from safetune.runner import harden

ap = argparse.ArgumentParser()
ap.add_argument("--method", required=True, choices=["plainsft", "safegrad"])
ap.add_argument("--data", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--safety"); ap.add_argument("--epochs", type=int, default=2); ap.add_argument("--lr", type=float, default=1e-4)
ap.add_argument("--bs", type=int, default=4); ap.add_argument("--seed", type=int, default=13)
ap.add_argument("--max-len", type=int, default=1024); ap.add_argument("--rho", type=float, default=0.1)
ap.add_argument("--limit", type=int, default=0); ap.add_argument("--grad-accum", type=int, default=4)
a = ap.parse_args()

# SafeTune's TrainingArguments builder has no knobs for gradient checkpointing or accumulation.
# Tiny Aya's 262k-token vocabulary makes logits large, so add both on top of SafeTune's own args.
from safetune.runner.harden import _base as _hb
_orig_args = _hb._HardenBase._training_args
def _training_args(self, out_dir):
    args = _orig_args(self, out_dir)
    args.gradient_checkpointing = True
    args.gradient_checkpointing_kwargs = {"use_reentrant": False}
    args.gradient_accumulation_steps = a.grad_accum
    return args
_hb._HardenBase._training_args = _training_args

data = a.data
if a.limit:
    data = a.data + f".head{a.limit}.jsonl"
    with open(a.data) as f, open(data, "w") as g:
        for i, l in enumerate(f):
            if i >= a.limit: break
            g.write(l)

safetune.configure(seed=a.seed, max_len=a.max_len)
common = dict(model_id="CohereLabs/tiny-aya-global", epochs=a.epochs, batch_size=a.bs, lr=a.lr)
t = time.time()
if a.method == "plainsft":
    tr = harden.PlainSFTTrainer(**common)
    path = tr.train(data, out_dir=a.out)
else:
    tr = harden.SafeGradTrainer(rho=a.rho, reference_model_path="CohereLabs/tiny-aya-global", **common)
    path = tr.train(data, out_dir=a.out, safety_dataset=a.safety)
info = dict(vars(a), seconds=round(time.time() - t), saved=path)
json.dump(info, open(os.path.join(path, "train_info.json"), "w"), indent=1)
print("TRAINED", json.dumps(info))
