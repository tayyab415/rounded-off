"""Gate 0b: CircuitKIT GPTQ W4 on Tiny Aya with proper calibration (default wikitext-2, 128 x 512)."""
import sys, time, torch
import circuitkit as ck
from transformers import AutoModelForCausalLM, AutoTokenizer
from circuitkit.applications.quantization.llmcompressor_quantize import llmcompressor_circuit_quantize
mid = "CohereLabs/tiny-aya-global"; out = sys.argv[1]; bits = int(sys.argv[2])
tok = AutoTokenizer.from_pretrained(mid)
m = AutoModelForCausalLM.from_pretrained(mid, dtype=torch.bfloat16, device_map="cuda")
t = time.time()
llmcompressor_circuit_quantize(m, tok, q_head_scores={}, mlp_scores={}, n_layers=m.config.num_hidden_layers,
                               bits=bits, high_fraction=0.0, n_calibration_samples=128, max_seq_length=512)
print("quantized", round(time.time() - t, 1), "s")
ck.export_checkpoint(m, None, out, intervention="quantization", tokenizer_name=mid)
print("exported", out)
