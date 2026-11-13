"""Gate 0: does CircuitKIT's llm-compressor path quantize Tiny Aya to W4 and reload?"""
import time, sys, torch
import circuitkit as ck  # must import before transformer_lens
from transformers import AutoModelForCausalLM, AutoTokenizer
from circuitkit.applications.quantization.llmcompressor_quantize import llmcompressor_circuit_quantize

mid = "CohereLabs/tiny-aya-global"
out = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/work/ckpt/smoke_w4"
tok = AutoTokenizer.from_pretrained(mid)
t = time.time()
m = AutoModelForCausalLM.from_pretrained(mid, dtype=torch.bfloat16, device_map="cuda")
print("loaded", round(time.time() - t, 1), "s", m.config.model_type, m.config.num_hidden_layers)
texts = ["How do I block my debit card if I lose it?", "मेरा कार्ड खो गया है, मैं उसे कैसे ब्लॉक करूँ?"] * 16
t = time.time()
res = llmcompressor_circuit_quantize(m, tok, q_head_scores={}, mlp_scores={}, n_layers=m.config.num_hidden_layers,
                                     bits=4, high_fraction=0.0, calibration_texts=texts, n_calibration_samples=32, max_seq_length=256)
print("quantized", round(time.time() - t, 1), "s", type(res))
ck.export_checkpoint(m, None, out, intervention="quantization", tokenizer_name=mid)
print("exported to", out)
