"""Round-to-nearest (RTN) weight quantization, saved as bf16 'fake-quant' weights.

Every nn.Linear inside model.layers gets symmetric per-group quantization (group along the input dim);
embeddings and lm_head stay bf16 (same scope as CircuitKIT/llm-compressor, which skips lm_head).
The saved weights are exactly the dequantized values, so behaviour equals a real W-only int kernel.
Usage: python quant_rtn.py SRC_DIR_OR_ID OUT_DIR --bits 4 --group 128 [--protect-layers 3,7,...]
"""
import argparse, json, os, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def rtn_(w: torch.Tensor, bits: int, group: int) -> torch.Tensor:
    out_f, in_f = w.shape
    g = group if in_f % group == 0 else in_f
    x = w.float().reshape(out_f, in_f // g, g)
    qmax = 2 ** (bits - 1) - 1
    scale = x.abs().amax(dim=-1, keepdim=True).clamp(min=1e-8) / qmax
    q = torch.clamp(torch.round(x / scale), -qmax - 1, qmax)
    return (q * scale).reshape(out_f, in_f).to(w.dtype)

def quantize_model_(model, bits, group, protect=()):
    n = 0
    for name, mod in model.named_modules():
        if isinstance(mod, torch.nn.Linear) and ".layers." in name:
            layer = int(name.split(".layers.")[1].split(".")[0])
            if layer in protect: continue
            with torch.no_grad(): mod.weight.copy_(rtn_(mod.weight, bits, group))
            n += 1
    return n

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--bits", type=int, default=4); ap.add_argument("--group", type=int, default=128)
    ap.add_argument("--protect-layers", default="")
    a = ap.parse_args()
    protect = {int(x) for x in a.protect_layers.split(",") if x}
    tok = AutoTokenizer.from_pretrained(a.src)
    m = AutoModelForCausalLM.from_pretrained(a.src, dtype=torch.bfloat16, device_map="cuda")
    n = quantize_model_(m, a.bits, a.group, protect)
    m.save_pretrained(a.out); tok.save_pretrained(a.out)
    json.dump({"src": a.src, "method": "rtn-symmetric", "bits": a.bits, "group": a.group,
               "protect_layers": sorted(protect), "n_linear_quantized": n}, open(os.path.join(a.out, "quant_info.json"), "w"), indent=1)
    print(f"RTN W{a.bits} g{a.group}: {n} linears quantized, protect={sorted(protect)} -> {a.out}")
