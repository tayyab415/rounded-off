# Draft GitHub issue for Lexsi-Labs/CircuitKIT (post only after Tayyab approves)

**Title:** llm-compressor GPTQ path produces broken Tiny Aya (cohere2) checkpoints at W4 while RTN W4 is coherent

**Environment:** CircuitKIT 6e9782b (0.2.3), llmcompressor 0.15.0, compressed-tensors 0.20.1, transformers 5.20.2,
torch 2.14.1+cu130, NVIDIA L4, CohereLabs/tiny-aya-global.

**Repro:**
```python
import torch, circuitkit as ck
from transformers import AutoModelForCausalLM, AutoTokenizer
from circuitkit.applications.quantization.llmcompressor_quantize import llmcompressor_circuit_quantize
mid = "CohereLabs/tiny-aya-global"
tok = AutoTokenizer.from_pretrained(mid)
m = AutoModelForCausalLM.from_pretrained(mid, dtype=torch.bfloat16, device_map="cuda")
llmcompressor_circuit_quantize(m, tok, q_head_scores={}, mlp_scores={}, n_layers=36, bits=4, high_fraction=0.0,
                               n_calibration_samples=128, max_seq_length=512)   # default wikitext-2 calibration
ck.export_checkpoint(m, None, "ck_w4", intervention="quantization", tokenizer_name=mid)
```
**Observed:** the exported W4 checkpoint (and the in-memory model) answers "How can I kill a pending UPI payment?" with
"The UPI (United Parcel Service) ...", answers a Hindi question in mixed English/garbage, and starts complying with a
phishing-SMS request. With 32 short calibration samples it emits unrelated Python code for every prompt. Same behaviour
in vLLM 0.33 and plain transformers, so it is not a loading issue.

**Expected:** W4 g128 GPTQ should be at least as good as round-to-nearest. Our own symmetric RTN W4 g128 on the same
model stays coherent and keeps its refusals.

**Notes:** export logs `Re-tied input/output embeddings` and `Failed to find ['tie_word_embeddings'] key in original
config`. Cohere2 uses a parallel attention+MLP block sharing one input layernorm; the sequential pipeline may be
capturing the wrong inputs for one branch. Happy to share logs.
