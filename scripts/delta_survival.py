"""How much of a weight change survives round-to-nearest quantization?

For a variant X derived from the aligned model M0 (fine-tune or repair), delta = W_X - W_M0 on every Linear in
model.layers. For each (bits, group) we report, aggregated over all layers and per layer:
  rel_delta       ||delta|| / ||W_M0||
  sub_half_step   share of changed weights with |delta| < step/2 (step = group absmax / qmax of W_M0)
  cos_kept        cosine(Q(W_X) - Q(W_M0), delta): direction of the change that survives rounding
  kept_coef       <Q(W_X) - Q(W_M0), delta> / ||delta||^2: how much of the change survives on average
  noise_ratio     ||Q(W_X) - W_X|| / ||delta||: rounding noise relative to the change
Usage: python delta_survival.py OUT.json X_PATH [X_PATH ...] --bits 4 3 --group 128
"""
import argparse, json, os, sys, torch
from safetensors import safe_open
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_rtn import rtn_

def tensors(path):
    if not os.path.isdir(path):
        from huggingface_hub import snapshot_download
        path = snapshot_download(path, allow_patterns=["*.safetensors", "*.json"])
    out = {}
    for f in sorted(os.listdir(path)):
        if f.endswith(".safetensors"):
            with safe_open(os.path.join(path, f), "pt") as h:
                for k in h.keys():
                    if ".layers." in k and k.endswith(".weight") and h.get_slice(k).get_shape().__len__() == 2:
                        out[k] = (os.path.join(path, f), k)
    return out

def load(ref):
    with safe_open(ref[0], "pt", device="cuda") as h: return h.get_tensor(ref[1])

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("variants", nargs="+")
ap.add_argument("--bits", type=int, nargs="+", default=[4, 3]); ap.add_argument("--group", type=int, default=128)
ap.add_argument("--base", default="CohereLabs/tiny-aya-global")
a = ap.parse_args()
B = tensors(a.base); res = {}
for v in a.variants:
    X = tensors(v); res[v] = {}
    for bits in a.bits:
        qmax = 2 ** (bits - 1) - 1
        agg = dict(dd=0.0, w0=0.0, dot=0.0, qq=0.0, nz=0, sub=0, noise=0.0); per_layer = {}
        for k, ref in B.items():
            if k not in X: continue
            w0 = load(ref).float(); wx = load(X[k]).float(); d = wx - w0
            if d.abs().max() == 0: continue
            q0, qx = rtn_(w0, bits, a.group).float(), rtn_(wx, bits, a.group).float()
            dq = qx - q0
            out_f, in_f = w0.shape; g = a.group if in_f % a.group == 0 else in_f
            step = (w0.reshape(out_f, in_f // g, g).abs().amax(-1, keepdim=True) / qmax).expand(-1, -1, g).reshape(out_f, in_f)
            changed = d != 0
            s = dict(dd=float((d * d).sum()), w0=float((w0 * w0).sum()), dot=float((dq * d).sum()), qq=float((dq * dq).sum()),
                     nz=int(changed.sum()), sub=int(((d.abs() < step / 2) & changed).sum()), noise=float(((qx - wx) ** 2).sum()))
            for kk in agg: agg[kk] += s[kk]
            layer = int(k.split(".layers.")[1].split(".")[0])
            pl = per_layer.setdefault(layer, dict(dd=0.0, dot=0.0, qq=0.0))
            for kk in pl: pl[kk] += s[kk]
        fin = lambda s: dict(cos_kept=s["dot"] / ((s["qq"] * s["dd"]) ** 0.5 + 1e-30), kept_coef=s["dot"] / (s["dd"] + 1e-30))
        res[v][f"w{bits}g{a.group}"] = dict(rel_delta=(agg["dd"] / agg["w0"]) ** 0.5, sub_half_step=agg["sub"] / max(1, agg["nz"]),
                                           noise_ratio=(agg["noise"] / agg["dd"]) ** 0.5, **fin(agg),
                                           per_layer={l: fin(s) for l, s in sorted(per_layer.items())})
        r = res[v][f"w{bits}g{a.group}"]
        print(f"{v} W{bits}: rel_delta={r['rel_delta']:.4f} sub_half_step={r['sub_half_step']:.3f} "
              f"cos_kept={r['cos_kept']:.3f} kept_coef={r['kept_coef']:.3f} noise_ratio={r['noise_ratio']:.2f}", flush=True)
json.dump(res, open(a.out, "w"), indent=1)
