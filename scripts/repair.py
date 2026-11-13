"""Post-hoc weight-space safety repair of the drifted checkpoint with SafeTune's recover pillar.

Methods (all from safetune.runner.recover):
  wiseft    WiseFTTrainer(aligned_model, alpha)        W = a*W_aligned + (1-a)*W_drift           (aligned only)
  safedelta SafeDeltaTrainer(aligned_model, strength)  keep delta entries that buy utility       (aligned only)
  resta     ReStaTrainer(base, aligned, alpha)         W = W_drift + a*(W_aligned - W_base)      (needs tiny-aya-base)
  lox       LoXTrainer(base, aligned, rank, factor)    low-rank safety-subspace extrapolation    (needs tiny-aya-base)
Usage: python repair.py --method wiseft --drift ckpt/M1 --out ckpt/M3_wiseft [--alpha 0.5] [--strength 0.1]
"""
import argparse, json, os, time, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from safetune.runner import recover

ap = argparse.ArgumentParser()
ap.add_argument("--method", required=True, choices=["wiseft", "safedelta", "resta", "lox"])
ap.add_argument("--drift", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--alpha", type=float, default=0.5); ap.add_argument("--strength", type=float, default=0.1)
ap.add_argument("--rank", type=int, default=8); ap.add_argument("--factor", type=float, default=0.3)
a = ap.parse_args()
ALIGNED, BASE = "CohereLabs/tiny-aya-global", "CohereLabs/tiny-aya-base"
load = lambda p, dev: AutoModelForCausalLM.from_pretrained(p, dtype=torch.bfloat16, device_map=dev)
t = time.time()
# Only the model being patched sits on the GPU; references stay in CPU RAM and are streamed per tensor.
# (Two 3.35B models on the 22 GB L4 plus fp32 temporaries for the 262k x 2048 embedding ran out of memory.)
drift = load(a.drift, "cuda"); aligned = load(ALIGNED, "cpu")
if a.method == "wiseft":
    tr = recover.WiseFTTrainer(drift, aligned_model=aligned, alpha=a.alpha); params = {"alpha": a.alpha}
elif a.method == "safedelta":
    tr = recover.SafeDeltaTrainer(drift, aligned_model=aligned, strength=a.strength); params = {"strength": a.strength}
elif a.method == "resta":
    base = load(BASE, "cpu")
    tr = recover.ReStaTrainer(drift, base_model=base, aligned_model=aligned, alpha=a.alpha, device="cuda"); params = {"alpha": a.alpha}
else:
    # LoXTrainer has no param_filter, so call SafeTune's apply_lox directly, limited to the transformer layers
    # (skips the 262k x 2048 tied embedding). aligned/base stay on CPU, so the SVDs run on CPU.
    from safetune.interventions.recover.lox import apply_lox
    base = load(BASE, "cpu")
    class _T:  # keep the same reporting shape as the trainer path
        def apply(self):
            return apply_lox(drift, base=base, aligned=aligned, rank=a.rank, extrapolation_factor=a.factor,
                             param_filter=["model.layers."])
    tr = _T(); tr.__class__.__name__ = "apply_lox(param_filter=model.layers.)"
    params = {"rank": a.rank, "factor": a.factor}
patched = tr.apply()
patched.save_pretrained(a.out); AutoTokenizer.from_pretrained(a.drift).save_pretrained(a.out)
info = {"method": a.method, "trainer": type(tr).__name__, "drift": a.drift, "aligned": ALIGNED, **params,
        "seconds": round(time.time() - t)}
json.dump(info, open(os.path.join(a.out, "repair_info.json"), "w"), indent=1)
print("REPAIRED", json.dumps(info))
