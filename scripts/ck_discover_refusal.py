"""CircuitKIT EAP-IG discovery of Tiny Aya's refusal circuit (harmful vs harmless prompts).

Writes the CircuitKIT artifact + score side-cars, and a per-layer importance ranking used to choose
which layers to keep at higher precision. Usage: python ck_discover_refusal.py contrast_prompts.json OUT_DIR [model]
"""
import json, sys, os, collections
import circuitkit as ck  # import before transformer_lens
from circuitkit.data.adapters.safety_prompt import SafetyPromptAdapter
from circuitkit.data.normalized_task import NormalizedTaskSpec

cp = json.load(open(sys.argv[1])); out = sys.argv[2]; mid = sys.argv[3] if len(sys.argv) > 3 else "CohereLabs/tiny-aya-global"
os.makedirs(out, exist_ok=True)
tl = ck.load_model(mid, dtype="bfloat16")
tok = tl.tokenizer
for t in ["I", " I", "Sure", " Sure"]:
    print("token", repr(t), tok.encode(t, add_special_tokens=False))
RT, CT = "I", "Sure"
ds = SafetyPromptAdapter().adapt([{"prompt": p} for p in cp["harmful"]], name="aya_refusal",
                                 pairing_mode="harmful_vs_benign", refusal_token=RT, compliance_token=CT,
                                 benign_controls=cp["harmless"])
ck.register_task(NormalizedTaskSpec(ds, name="aya_refusal"))
circuit = ck.discover(tl, "aya_refusal", algorithm="eap-ig", level="node", n_examples=64, batch_size=1,
                      ig_steps=3, output_path=os.path.join(out, "refusal.pt"))
print(circuit)
scores = {k: float(v) for k, v in (circuit.scores or {}).items()}
layer = collections.defaultdict(float)
for k, v in scores.items():
    if k.startswith("A") and "." in k: layer[int(k[1:].split(".")[0])] += abs(v)
    elif k.startswith("MLP"): layer[int(k.split()[1])] += abs(v)
rank = sorted(layer, key=lambda l: -layer[l])
json.dump({"model": mid, "refusal_token": RT, "compliance_token": CT, "n_examples": 64,
           "layer_importance": {str(l): layer[l] for l in sorted(layer)}, "layer_rank": rank,
           "top_nodes": sorted(scores.items(), key=lambda kv: -abs(kv[1]))[:40]},
          open(os.path.join(out, "layer_rank.json"), "w"), indent=1)
print("LAYER RANK", rank)
