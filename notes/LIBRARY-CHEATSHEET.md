# Lexsi libraries cheatsheet: Tiny Aya safety-drift project

Recon date 2026-11-12. Read-only pass over `vendor/`; nothing was run. Cites are `LIB:path:line`.
ST = vendor/SafeTune 0.1.12 (commit cc3de5f) · CK = vendor/CircuitKIT 0.2.3 (6e9782b) · AK = vendor/AuditKIT 1.1.11 (556eb48) · CU = vendor/CuratorKIT 0.1.21 (ed45ae3).
Facts tagged (PyPI) or (HF API) come from live queries on 2026-11-12, not from the repos. Estimates are tagged "est." and are not measured.

## 0. Quick answers

| Step | Simplest working call | Biggest catch |
|---|---|---|
| 1 SFT | `harden.PlainSFTTrainer(model_id="CohereLabs/tiny-aya-global").train("bank_sft.jsonl", out_dir="runs/drift")` | Saves a merged full checkpoint; loss on last assistant turn only |
| 2a SafeGrad/Lisa | `harden.SafeGradTrainer(model_id=...,rho=0.1).train(data, safety_dataset="refusals.jsonl")` | Default safety set is 6 English pairs; bring your own |
| 2b RESTA/LoX | `recover.ReStaTrainer(drifted, base_model=base, aligned_model=aligned, alpha=0.25, device="cpu").apply()` | Needs merged weights, not an adapter; alpha 1.0 breaks Tiny Aya |
| 2c Steering | `extract_refusal_direction(..., RefusalDirectionConfig(pick_layer=24))` then `RefusalDirectionModel(m, d, mode="steer", strength=a)` | Sweep is English-only and picks layer 1 unless fixed by hand |
| 3 Quantize | `ck.quantize(hf_model, circuit, backend="llmcompressor", bits=4, high_fraction=0.1, tokenizer=tok)` | Layer-granular protection; never run on Tiny Aya by the authors; pin conflicts |
| 4 Evaluate | AK `LLMJudge` + `ak.evaluate_many`, or ST `run_judge("wildguard", prompts, responses)` | Judges are English-trained; no multilingual benchmark anywhere |
| 5 Curate | `Curator(CuratorConfig(dataset="x.jsonl", dedup="minhash", pii_pseudonymize=True, toxicity_gate=True)).run()` | No web/HTML reader; PII and toxicity are English-centric |

Imports: `from safetune.runner import harden, recover` and `from safetune.steer import extract_refusal_direction, RefusalDirectionConfig, RefusalDirectionModel` (ST:README.md:185; ST:docs/user-guide/steer/activation-steering/refusal-direction-model.md:98-103).

## 1. Environment

- Python 3.12. ST needs >=3.12 (ST:pyproject.toml:10), CU >=3.11 (CU:pyproject.toml:10), CK and AK >=3.10 (CK:pyproject.toml:23, AK:pyproject.toml:10).
- Install order (torch first, matching your CUDA; do not use CK's `gpu-cu126` extra, it pins torch 2.10.0+cu126, CK:pyproject.toml:144):
```
pip install -e vendor/SafeTune -e vendor/CircuitKIT -e "vendor/AuditKIT[transformers,interop]" -e "vendor/CuratorKIT[all]"
pip install -e "vendor/CircuitKIT[quantization]"        # optimum-quanto only (CK:pyproject.toml:118-122)
pip install "llmcompressor>=0.15"                         # 0.15.0 is the 2026-10-28 release (PyPI); in no CK extra, see section 4
pip install "transformers>=5.16.1,<5.21" && python -c "import transformers;print(transformers.__version__)"
```
  AK docs warn pip can silently resolve transformers to 4.x; re-pin last and check (AK:docs/model_backends.md:180-205).
- Pins that interact:

| Package | Constraint | Source |
|---|---|---|
| transformers | ST and CK `>=5.15,<6` | ST:pyproject.toml:62, CK:pyproject.toml:62 |
| transformers | AK `[transformers]` `<5.22` (Aya-vision pipeline bug) | AK:pyproject.toml:29-37 |
| transformers | llmcompressor 0.15.0 `>=5.15,<=5.21.0`; vllm 0.33.0 `>=5.16.1,<5.21` | (PyPI) |
| transformers | llmcompressor 0.10.0.2 `<=4.57.6`: conflicts with ST/CK | (PyPI) |
| torch | ST `>=2.7`, CK `>=2.10`, vllm 0.33.0 `==2.14.0`, llmcompressor 0.15 `<=2.14.1` | ST:pyproject.toml:61, CK:pyproject.toml:51, (PyPI) |
| trl | ST `<1.15` (1.15.0 DPO needs a GPU at import) | ST:pyproject.toml:67-69 |
| transformer-lens | CK `==3.8.0`; TL 3.8.0 needs transformers `>=5.9.0` | CK:pyproject.toml:85, (PyPI) |
| compressed-tensors | llmcompressor 0.15 `==0.20.1`, vllm 0.33 `==0.17.0`: cannot share an env | (PyPI) |

- Verdict: ST + CK + AK(hf/api) + CU can share one env with transformers 5.16.1-5.20.x and no vLLM. vLLM and llm-compressor cannot share one env. Put vLLM in a second env and reach it through AK's `api:` backend or CU's `llm_api_base`.
- ST does not need TransformerLens: its own EAP is native HF hooks (ST:src/safetune/instrumentation/interpret/eap.py:78-80). Skip the `interpret` extra (ST:pyproject.toml:159).
- CK raises ImportError if `transformer_lens` is imported before `circuitkit` (CK:CHANGELOG.md:63-64). Import `circuitkit` first in every process.
- CK's own verified env is the NeMo 25.09 container with transformers 4.57.6, llmcompressor 0.10.0.2, torch 2.9 (CK:ENVIRONMENT.md:16-28, 51-54). That contradicts its pyproject (transformers >=5.15). Treat the quantization path as unverified on transformers 5.
- Tokens: `HF_TOKEN` with access to CohereLabs/tiny-aya-* (CK:ENVIRONMENT.md:76-90). Gated-auto (click-through): tiny-aya-global/base (CC-BY-NC-4.0), allenai/wildguard (Apache-2.0), walledai/XSTest, HarmBench, StrongREJECT, AdvBench (HF API). Manual gate: meta-llama/Llama-Guard-3-8B. Open: cais/HarmBench-Mistral-7b-val-cls (MIT), ibm-granite/granite-guardian-3.1-2b, bench-llm/or-bench, JBB-Behaviors (HF API).

## 2. Step 1: plain LoRA SFT (drift)

- Use ST's own plain trainer so every variant shares the pipeline: `PlainSFTTrainer` (ST:src/safetune/runner/harden/_gradient_surgery.py:17-28). CLI: `safetune train --algo plainsft --model CohereLabs/tiny-aya-global --train-dataset data/bank_sft.jsonl --train-split train --epochs 2 --batch-size 4 --lr 1e-4 --output runs/drift` (alias at ST:src/safetune/runner/_registry.py:19; flags ST:docs/reference/cli.md:37, 107-110).
- Constructor defaults: epochs 1, batch 4, lr 1e-4, bf16 auto (ST:src/safetune/runner/harden/_base.py:221-238). Without `--lr` the CLI uses the method's own rate, not 5e-5 (ST:CHANGELOG.md:129).
- LoRA is hard-wired: r=16, alpha=32, dropout 0.05, q/k/v/o/gate/up/down (ST:src/safetune/config.py:229-233; ST:src/safetune/runner/utils/model_utils.py:106-130). Change with `safetune.configure(lora_r=...)`. No path resumes an existing adapter: `_lora_base` always wraps a plain model (ST:src/safetune/runner/harden/_base.py:307-325).
- Output is a merged full checkpoint with tokenizer and `lexsi_provenance.json` (ST:src/safetune/runner/harden/_base.py:327-340; ST:src/safetune/runner/utils/model_utils.py:133-179). Default dir `results/checkpoints/<name>`.
- Data: JSONL rows as chat `messages`, ShareGPT `conversations`, Alpaca `instruction/input/output`, or `prompt/response`. Prompt-only rows are skipped, all-prompt-only raises (ST:src/safetune/runner/utils/data_utils.py:207-293; ST:docs/user-guide/harden.md:20-27). A path string works directly: `.train("data/bank_sft.jsonl")` (ST:src/safetune/runner/harden/_base.py:36-51, 257-271).
- Quirks that bite:
  - Loss is on the last assistant turn only (ST:src/safetune/runner/utils/data_utils.py:152-155). Split multi-turn chats into one row per assistant turn.
  - Every row is padded to one `max_len`, sized from the first 32 rows: `max(256, longest prompt + 256)`, capped 2048 (ST:src/safetune/runner/utils/data_utils.py:138-148, 168). Longer rows later in the file get truncated. Set `safetune.configure(max_len=1024)` after checking your longest row.
  - Tiny Aya's chat template adds ~366 system-preamble tokens per row (ST:README.md:253-256). An explicit `max_len` below that raises (ST:src/safetune/runner/utils/data_utils.py:187-191).
- Own TRL/PEFT run instead: you must `merge_and_unload()` and save a full checkpoint. RESTA/LoX and the hardened variants all need full weights.
- Memory (est.): bf16 weights 6.7 GB; rows padded to >=620 tokens; plan for a 24-40 GB GPU at batch 4.

## 3. Step 2: safety repair

### 3a. SafeGrad / Lisa (train-time)
- SafeGrad: `harden.SafeGradTrainer(model_id="CohereLabs/tiny-aya-global", rho=0.1, kl_temperature=1.0, reference_model_path=None).train("data/bank_sft.jsonl", out_dir="runs/safegrad", safety_dataset="data/refusals_en_hi.jsonl")` (ST:src/safetune/runner/harden/_gradient_surgery.py:38-93). Lisa: `LisaTrainer(..., lisa_rho=0.1, lisa_warmup_steps=10, lisa_alignment_step=20, lisa_finetune_step=20)` (ST:src/safetune/runner/harden/_data_shaping.py:16-70). CLI aliases `safegrad`, `lisa`; `--safety-dataset` takes a local file (ST:docs/reference/cli.md:110).
- Both audit as Faithful, as do `apply_resta` and `apply_lox` (ST:docs/reference/feature-map.md:44-45, 83, 89). Docs say start SafeGrad at rho 0.1, up to 0.5 (ST:docs/user-guide/harden/gradient-surgery.md:88); the class default is 1.0.
- Safety data: rows with `prompt`+`response` (refusals) or `messages`. If you pass none, SafeGrad and Lisa use 6 built-in English refusal pairs (ST:src/safetune/runner/utils/data_utils.py:369-383; ST:src/safetune/runner/harden/_gradient_surgery.py:94-97, ST:src/safetune/runner/harden/_data_shaping.py:52-54). Supply your own EN+Hindi set, or `safetune.configure(datasets={"safety_refusals": "refusals.jsonl"})` (ST:src/safetune/data/dataset_ids.py:92). Loss is on the refusal only (ST:CHANGELOG.md:84).
- SafeGrad loads a frozen reference from `reference_model_path` or the tokenizer's id, so pass `model_id="CohereLabs/tiny-aya-global"` (ST:src/safetune/runner/harden/_gradient_surgery.py:63-69). Adds a second 6.7 GB model plus a safety batch (est. +10 GB). The doc says ~2x plain SFT memory (ST:docs/user-guide/harden/gradient-surgery.md:84).
- Same LoRA/merge/save path as step 1, so results compare cleanly with PlainSFT.

### 3b. RESTA and LoX (weight-space, no training)
- Roles for Tiny Aya: base = `CohereLabs/tiny-aya-base`, aligned = `CohereLabs/tiny-aya-global`, drifted = the merged step-1 checkpoint. RESTA with DARE requires the drifted model to be fine-tuned from `aligned` (ST:src/safetune/interventions/recover/resta.py:73-75).
- RESTA: `recover.ReStaTrainer(drifted, base_model=base, aligned_model=aligned, alpha=0.25, dare=True, dare_drop_rate=None, device="cpu").apply()` (ST:src/safetune/runner/recover/_layer.py:43-67). Math: `aligned + DARE(ft - aligned, p=0.3) + alpha*(aligned - base)`; `dare=False` is plain `ft + alpha*v` (ST:src/safetune/interventions/recover/resta.py:139-147).
- Tiny Aya: alpha 1.0 breaks the model; 0.1 and 0.25 restore refusal with normal answers, >=0.5 breaks it (ST:docs/user-guide/recover/layer/resta.md:64; ST:src/safetune/runner/recover/_layer.py:14-16). Sweep alpha {0.1,0.25,0.4}.
- LoX: `recover.LoXTrainer(drifted, base_model=base, aligned_model=aligned, rank=8, extrapolation_factor=0.3).apply()` (ST:src/safetune/runner/recover/_low_rank.py:29-45). Adds `factor * LowRank_k(aligned - base)` to the drifted weights (ST:src/safetune/interventions/recover/lox.py:86-98, 130-143). Audit badge Faithful for `apply_lox`, but the paper's LoX hardens the aligned model before fine-tuning; the trainer's own docstring says the defaults gave only a small correction on a 0.5B model (ST:src/safetune/runner/recover/_low_rank.py:18-24). The pre-fine-tune variant is `LoXHardenTrainer` (ST:docs/user-guide/harden.md:103). The function-level defaults differ (`rank=64`, `factor=1.5`, ST:src/safetune/interventions/recover/lox.py:50-51). Sweep rank and factor.
- Inputs must be full models (nn.Module with matching state-dict keys). A PEFT-wrapped drifted model has different keys: RESTA skips them without error (ST:src/safetune/interventions/recover/resta.py:135-137) and the mutation check only logs a warning (ST:src/safetune/interventions/recover/_invariant.py:1-25). Merge adapters first.
- Save: `trainer.save_checkpoint(patched, tokenizer, "resta_a025")` writes under `results/checkpoints/` (ST:src/safetune/runner/recover/_base.py:87-92). CLI `safetune patch --algo resta --model drifted --base base --aligned aligned --alpha 0.25 --output out` also saves (ST:src/safetune/cli.py:185-221); the doc example omits `--aligned`, which ReSta needs (ST:docs/reference/cli.md:59-64).
- Memory: three bf16 models = ~20 GB (est.). Keep base and aligned on CPU with `device="cpu"`; the safety vector is streamed per tensor (ST:docs/user-guide/recover/layer/resta.md:67-79). LoX has no `device` argument and does an fp32 SVD per weight, including the 262144x2048 embedding (ST:src/safetune/interventions/recover/lox.py:122-131); expect a 24 GB GPU or slow CPU runs (est.).

### 3c. RefusalDirection steering (inference time)
- Steps: pick prompts; `d, layer, per_layer = extract_refusal_direction(model, tok, harmful, harmless, RefusalDirectionConfig(pick_layer=24))` from `safetune.steer`; `wrapped = RefusalDirectionModel(model, direction=d, mode="steer", strength=alpha)`; `with wrapped: wrapped.generate(**inputs)` (ST:src/safetune/interventions/steer/refusal_direction.py:179, 596-690, 722).
- Use the functions, not the trainer. `RefusalDirectionTrainer.calibrate` calls extraction with no config, so you cannot set `pick_layer` through it (ST:src/safetune/runner/steer/_activation.py:36-48). Trainer default alpha is 20, "far too strong" even on 0.5B (ST:README.md:210-214). `steer` adds `alpha * unit_direction` at every selected layer; sweep alpha from ~0.1 upward on Tiny Aya (est.).
- Tiny Aya: the sweep without the layer floor picked layer 1 of 36; fix by hand at 24 of 36 (ST:docs/user-guide/steer/activation-steering/refusal-direction-model.md:60-64; ST:README.md:258-260). Floor field `min_layer_fraction=0.2` (ST:src/safetune/interventions/steer/refusal_direction.py:125).
- Calibration prompts: any lists of strings. Defaults pull BeaverTails and Alpaca (English; CC-BY-NC-4.0, HF API) (ST:src/safetune/runner/utils/data_utils.py:402-436). Pass your own EN+Hindi harmful/harmless lists. The sweep's refusal check is an English substring list (ST:src/safetune/interventions/steer/refusal_direction.py:136-175), so it cannot see Hindi refusals; use `pick_layer`.
- Works on a PEFT or merged model (layers found through `get_base_model`, ST:src/safetune/_refusal_helpers.py:13-34). No weights change; hooks live only inside `with`/`install()`. ST's `evaluate()` accepts the wrapper (ST:src/safetune/instrumentation/evaluate/suite/evaluate.py:530-575). AK cannot apply the hooks itself; pass AK a callable `list[str] -> list[str]` that calls `wrapped.generate` (AK:docs/model_backends.md:9).
- Weight-space alternative: `orthogonalize_weights` is the attack direction, not a repair (ST:docs/user-guide/steer/activation-steering/refusal-direction-model.md:107-136).

### 3d. Finding safety-relevant components (feeds step 3)
- `identify_safety_neurons(model, per_layer_directions, config=SafetyNeuronConfig(method="weight"|"activation", top_k_per_layer=16))` returns `report.per_layer = {layer: [(neuron, score)]}` (ST:src/safetune/instrumentation/interpret/safety_neurons.py:512; ST:docs/user-guide/interpret/safety-neurons/weight.md:12-33). Activation mode takes `harmful_prompts`, `harmless_prompts`, `tokenizer` (ST:docs/user-guide/interpret/safety-neurons/activation.md:6-15). Both modes are badge Variant (ST:docs/reference/feature-map.md:185-186). It strips the duplicate BOS and keeps the prompt end for long templates (ST:CHANGELOG.md:55, 70).
- `eap_safety_circuit(model, harmful, harmless, EAPSafetyCircuitConfig(method="eap-ig", granularity="head", top_k_edges=100, ig_steps=3, batch_size=2, max_seq_len=512, output_dir="runs/eap"))` writes `eap_scores.json` with `all_scores` keyed `blocks.<L>.attn.head<H>` and `blocks.<L>.mlp` (ST:src/safetune/instrumentation/interpret/eap.py:93-147, 792-802, 850-890). Default `max_seq_len=64` is too short for Tiny Aya's preamble; the left-cut fix keeps the prompt tail (ST:CHANGELOG.md:121-124). Metric tokens default to first sub-tokens of "I" vs "Sure" (ST:src/safetune/instrumentation/interpret/eap.py:140-141, 200-211). Badge Simplified (ST:docs/reference/feature-map.md:190).

## 4. Step 3: CircuitKIT quantization

### 4a. Discovery (get circuit scores)
- Load: `import circuitkit as ck; tl = ck.load_model("CohereLabs/tiny-aya-global", dtype="bfloat16")` (CK:src/circuitkit/quick.py:260). Tiny Aya (cohere2) runs through CK's TransformerLens port; the five tiny-aya repos are registered, local checkpoint dirs resolve from `config.json` (CK:docs/advanced/tiny-aya.md:30-38; CK:src/circuitkit/backends/_tl_compat/cohere.py:213-232; CK:src/circuitkit/quick.py:157-216). Needs `HF_TOKEN`.
- Safety contrast task (no built-in one for custom data; registered helpers cover advbench/harmbench/sorrybench/jailbreakbench, CK:src/circuitkit/tasks/safety_datasets.py:101-117):
```
from circuitkit.data.adapters.safety_prompt import SafetyPromptAdapter
from circuitkit.data.normalized_task import NormalizedTaskSpec
raw = [{"prompt": p} for p in harmful_prompts]               # any column in _PROMPT_COLS, adapter lines 36-47
ds = SafetyPromptAdapter().adapt(raw, name="bank_refusal", pairing_mode="harmful_vs_benign",
        refusal_token=" I", compliance_token=" Sure", benign_controls=harmless_prompts)
ck.register_task(NormalizedTaskSpec(ds, name="bank_refusal"))
circuit = ck.discover(tl, "bank_refusal", algorithm="eap-ig", level="node", n_examples=64,
                      batch_size=1, ig_steps=3, output_path="runs/ck/refusal.pt")
```
  (CK:src/circuitkit/data/adapters/safety_prompt.py:56-57, 160-186; CK:src/circuitkit/tasks/safety_datasets.py:75-98; CK:src/circuitkit/quick.py:465-545.) `ck.quantize` needs `circuit.scores` with `A<l>.<h>` and `MLP <l>` names (CK:src/circuitkit/quick.py:869-890).
- Answer tokens must be single tokens in the Cohere tokenizer; defaults " I"/" Sure" are GPT-2/Llama style and unverified for Tiny Aya (CK:docs/advanced/tiny-aya.md:139-151). Check `tok.encode` before a run.
- Custom tasks default to chat template "auto", so the ~366-token preamble gets prepended and EAP-IG memory grows with it (CK:docs/advanced/chat-templates.md:26). Consider `chat_template_mode="off"` or a short system prompt.
- Discovery is validated on Tiny Aya only for `greater_than`, not refusal tasks (CK:docs/advanced/tiny-aya.md:139-151). Registry status is EXPERIMENTAL (CK:src/circuitkit/applications/arch_registry.py:142).
- Memory: no Tiny Aya number in the docs. Llama-3.2-1B peaks at 4.1 GB with batch 1, ig_steps 3 (CK:docs/advanced/memory-optimization.md:14-16). TL keeps a separate W_U (CK:docs/advanced/experimental-models.md:367-369). Est. 12-20 GB for 3.35B at batch 1.
- Memory (quantize): llm-compressor's `sequential` pipeline works layer by layer (CK:src/circuitkit/applications/quantization/llmcompressor_quantize.py:350-358), so 3.35B should fit a 24 GB GPU (est.). CK's own runs used one 140 GB H200 and say smaller GPUs need smaller `batch_size` (CK:ENVIRONMENT.md:70-74).
- Quantization needs a merged full HF model; the layer-name patterns assume `model.layers.N...`, so a PEFT-wrapped model will not match (inference from CK:src/circuitkit/applications/quantization/quant_utils.py:347-391).
- One discovery on tiny-aya-global can protect every variant (same 36 layers). Re-running per variant is optional.
- Alternative score source: ST `eap_safety_circuit` or `identify_safety_neurons` (3d). Convert by hand to `q_head_scores={(L,H): s}` and `mlp_scores={L: s}` and call the low-level function below; no converter exists in either repo. ST can read CK `*_scores.json` (ST:src/safetune/core/circuit_kit/adapter.py:23, 74, 209), not the reverse.

### 4b. Quantize
- True low-bit (recommended): `ck.quantize(hf_model, circuit, backend="llmcompressor", bits=4, high_fraction=0.1, tokenizer=tok, calibration_texts=texts, n_calibration_samples=128, max_seq_length=512)` (CK:src/circuitkit/quick.py:813-931; CK:src/circuitkit/applications/quantization/llmcompressor_quantize.py:207-372). `hf_model = AutoModelForCausalLM.from_pretrained(ckpt)`, modified in place; discovery model is the separate TL copy.
  - bits in {3,4,8}; weight-only GPTQ via `llmcompressor.oneshot`, group_size 128, symmetric, `lm_head` always skipped (CK:src/circuitkit/applications/quantization/llmcompressor_quantize.py:66, 219-221, 350-358).
  - Protection is whole layers: top `high_fraction` by circuit score plus `protect_layers`, attention and MLP together, left at native bf16 via `ignore=[re:model\.layers\.N\..*]` (CK:src/circuitkit/applications/quantization/llmcompressor_quantize.py:96-129, 132-159). No per-head or per-neuron protection.
  - Uniform baseline: `high_fraction=0.0`. If you have no circuit, call `llmcompressor_circuit_quantize(model, tok, q_head_scores={}, mlp_scores={}, n_layers=36, bits=4, high_fraction=0.0)` directly. Random or SafeTune-chosen protection: pass `protect_layers=[...]` with `high_fraction=0.0` (explicit list wins, same file:149-159).
  - `ck.quantize` raises on a circuit without scores (CK:src/circuitkit/quick.py:869-873).
  - Calibration defaults to wikitext-2 from the Hub; pass `calibration_texts` (banking plus refusal text, EN+HI) (CK:src/circuitkit/applications/quantization/llmcompressor_quantize.py:165-201).
  - Embedding (tied, 262144x2048 = 537M params of 3.35B) is not a Linear, so `targets=["Linear"]` should leave it bf16 (inference from llmcompressor_quantize.py:316-332; not tested). Report effective bits/weight and bytes on disk.
- quanto backend: `ck.quantize(hf_model, circuit, backend="quanto", high_fraction=0.1, low_weights=qint4, high_weights=None)`; no 3-bit (qint2/4/8 only) and `bits` is ignored (CK:src/circuitkit/applications/quantization/llmcompressor_quantize.py:5-9; CK:docs/user-guide/applications.md:110-111). Tiers are ranked separately for attention and MLP (CK:src/circuitkit/applications/quantization/quant_utils.py:110-185). qint4 kernels JIT-compile with nvcc and need sm80+ (`CUDA_HOME`, `TORCH_CUDA_ARCH_LIST`) (CK:src/circuitkit/applications/quantization/examples/quantize_qwen.py:57-97). `random_quantize` is a built-in matched-fraction random control (quant_utils.py:246).
- Export: `ck.export_checkpoint(hf_model, None, "runs/q/resta_w4", intervention="quantization", tokenizer_name="CohereLabs/tiny-aya-global")` (CK:src/circuitkit/quick.py:950-1018; CK:src/circuitkit/evaluation/hf_checkpoint.py:952-1010).

| Backend | What is on disk | Reload |
|---|---|---|
| llmcompressor | real packed int weights (`pack-quantized`), `quantization_config` in config.json | `AutoModelForCausalLM.from_pretrained` with compressed-tensors installed; vLLM-native (CK:src/circuitkit/evaluation/hf_checkpoint.py:830-907, 934-949) |
| quanto | quanto-packed tensors + `quanto_qmap.json` | only `load_quantized_checkpoint` (CK:src/circuitkit/evaluation/hf_checkpoint.py:1121); plain transformers/vLLM cannot load it |
| quanto, dequantized | `export_dequantized_checkpoint` writes bf16 weights holding the quantization error: fake-quant, no memory saving | plain transformers and vLLM (CK:src/circuitkit/evaluation/hf_checkpoint.py:1209-1248) |

- CLI: `circuitkit quantize --model ckpt --artifact runs/ck/refusal.pt --bits 4 --high-fraction 0.1 --backend llmcompressor --output out` (CK:docs/cli/applications.md:28-41).
- Not validated on Tiny Aya: CK says target-module patterns were checked on real Cohere models, but quanto `quantize()/freeze()` was NOT run and llmcompressor is optional and not exercised in every env (CK:src/circuitkit/applications/arch_registry.py:161-166; CK:README.md:130-137). Cohere family module names resolve as `model.layers.N.self_attn.*` and `mlp.*` (CK:src/circuitkit/applications/arch_registry.py:123-140).
- llmcompressor is not in any CK extra, though CK docs say `[quantization]` suffices (CK:pyproject.toml:118-122; CK:docs/contributing/testing-on-cuda.md:127-128). The API calls (`GPTQModifier(config_groups=..., ignore=..., dampening_frac=...)`, `oneshot(..., pipeline="sequential")`) were written against 0.10.0.2; 0.15 is untested here.
- Also in CK, for the paper: `compute_ppl` (quant_utils.py:724) and `ck.benchmark(path, tasks, backend="hf"|"vllm")` for lm-eval (CK:src/circuitkit/quick.py:1048). Docs report 3-bit separates selectors only at >=15% protected layers (CK:docs/reference/hyperparameters.md:141).

## 5. Step 4: evaluation

### 5a. AuditKIT (recommended for LLM-judge, EN+HI, own JSONL)
- Data: `ak.load_jsonl("data/eval_harm_hi.jsonl")`; key `input` required, `target` optional, other keys go to `metadata` (AK:src/auditkit/loaders.py:248-292). `field_map={"prompt":"input"}` renames. CSV, CuratorKIT folders (`ak.load_dataset(path, "sft_alpaca")`) also load (AK:src/auditkit/loaders.py:120-167).
- Model specs: `hf:<dir or hub id>` (merged checkpoint, or a PEFT adapter folder, needs peft) (AK:src/auditkit/model/hf_gen.py:226-234); `vllm:<id>`; `api:<model>` with `api_base`, `api_key` for a vLLM/SGLang server; any `list[str] -> list[str]` callable (AK:docs/model_backends.md:5-12, 60-72). The prefix is mandatory. Chat templates are applied by `hf:`/`vllm:`; Tiny Aya's named template and double-BOS bugs are fixed (AK:CHANGELOG.md:260-265). Pass `RunConfig(max_tokens=256, temperature=0.0)` (AK:src/auditkit/runspec.py:25-52).
- Harmful compliance and over-refusal with an LLM judge (any model spec as judge, custom prompt, so Hindi prompts work):
```
judge = ak.LLMJudge(judge_model="openai:gpt-4o-mini", name="complied", temperature=0.0, use_cot=True,
   prompt="...<request>{input}</request><response>{output}</response> Did the assistant comply with the harmful request?",
   choices={"refused":0.0,"partial":0.5,"complied":1.0}, direction=ak.Direction.MINIMIZE)
res = ak.evaluate_many({"harm_en":(harm_en,[judge]), "harm_hi":(harm_hi,[judge]), "benign_en":(benign_en,[over_judge]),
   "bank_en":(bank_en,["quasi_exact_match"])}, model="hf:runs/resta_a025", config=ak.RunConfig(max_tokens=256))
```
  (AK:docs/examples/many_datasets.md:26-60; AK:src/auditkit/metrics/judge.py:166-262.) `evaluate_many` loads the model once. An unparseable verdict is flagged `unknown` and left out of the mean unless `unknown_score` is set (AK:src/auditkit/metrics/judge.py:185-190, 334-345). `api:` judges get a 600 s timeout (`AUDITKIT_JUDGE_TIMEOUT`, AK:src/auditkit/metrics/judge.py:44-48, 85-95).
- Banking accuracy scorers: `exact_match`, `quasi_exact_match`, `f1_score`, `rouge_l`, `chrf`, `levenshtein`, plus `Factuality`/`ClosedQA` judges (AK:docs/scorers_reference.md:23-24, 37, 40, 54-55, 85-86).
- Guard models as scorers: `GuardJudge(profile=...)`; default `llama_guard` = `hf:meta-llama/Llama-Guard-3-8B` (manual gate); `wildguard` = `allenai/wildguard`; open options `harmbench` (`cais/HarmBench-Llama-2-13b-cls`) and `granite_guardian` (AK:docs/guard_models.md:59-71, 147-166). Swap by `judge_model=` any `hf:|vllm:|groq:|api:` spec.
- No bundled benchmarks or multilingual sets: load HarmBench, XSTest, etc. yourself (AK:docs/guard_models.md:296-297). Red-team probes and a regex `RefusalDetector` exist (English patterns, AK:src/auditkit/redteam/detectors/builtin.py:37-65).
- Tiny Aya on AK: `hf:` 4/5 and `vllm:` 4/5 on five-language probes; the Hindi answer differs between GPUs and transformers versions (AK:docs/model_backends.md:97-111). vLLM 0.30.0 + transformers 5.16.1 measured (AK:docs/model_backends.md:90-93).
- Known gaps: `evaluate()` does not free a `vllm:` model between calls (construct `VLLMModel` and call `.unload()`, AK:docs/VLLM_KNOWN_ISSUES.md:51-85).
- Compressed-tensors checkpoints through `hf:` should work if compressed-tensors is installed; not tested by AK or CK for Tiny Aya.

### 5b. SafeTune evaluate (English benchmarks, local classifier judges)
- `from safetune.evaluate import evaluate; evaluate(model, tokenizer=tok, benchmarks=["harmbench","xstest"], judge="wildguard", max_prompts=100, max_new_tokens=256)` (ST:src/safetune/instrumentation/evaluate/suite/evaluate.py:178-266). Takes a loaded HF model or steering wrapper, not a path. Returns `asr`, `refusal_rate`, `harmfulness_score`, `n_evaluated`; XSTest reports the safe-prompt refusal rate (over-refusal) plus `safe`/`unsafe` blocks (same file:236-238, 330-344).
- Judges: `wildguard` default = `allenai/wildguard` (gated-auto, ~14.5 GB), `harmbench` = `cais/HarmBench-Mistral-7b-val-cls` (open), `llama_guard_3` = `meta-llama/Llama-Guard-3-8B` (manual gate) (ST:src/safetune/instrumentation/evaluate/suite/evaluate.py:66-70; ST:README.md:242-249). Over-refusal sets require `wildguard` (same file:277-285). Target and judge are loaded in one process: plan ~24 GB+ (est.).
- WildGuard score counts any reply that lacks "response refusal: yes" as compliance (ST:src/safetune/instrumentation/evaluate/suite/evaluate.py:395; ST:src/safetune/instrumentation/evaluate/judges/_parsers.py:17-18). It measures non-refusal, not harm. Off-topic or garbled Hindi output scores as compliance.
- Swap judge: `safetune.configure(judges={"wildguard": {"model_id": "<mirror or local copy>"}})` keeps the WildGuard template, so only compatible models work (ST:src/safetune/instrumentation/evaluate/suite/evaluate.py:73-74; HarmBench needs a known template id, ST:src/safetune/instrumentation/evaluate/judges/_templates.py:81-100). An OpenAI-compatible LLM judge exists as `OpenAIJudge(OpenAIJudgeConfig(model, api_base, api_key_env))` with the StrongREJECT autograder prompt, but `evaluate()` does not call it (ST:src/safetune/core/eval/pipeline/scorer.py:388-470; ST:docs/user-guide/evaluate/judges/index.md:46-49).
- Decoupled scoring: generate yourself (e.g. vLLM), then `run_judge("wildguard", prompts, responses)` returns 0/1 per pair (ST:src/safetune/instrumentation/evaluate/judges/__init__.py:341-387). Registry: harmbench, wildguard, sorrybench, hexphi/orbench/ailuminate (gated Llama-3.1-8B-Instruct), advbench string-match (same file:41-77).
- Benchmarks registered for `evaluate()`: harmbench (400, walledai/HarmBench), wildjailbreak, sorrybench_v1, advbench, hexphi, ailuminate, orbench_hard/orbench_toxic, xstest (250 safe + 200 unsafe), jailbreakbench, beavertails, star1, gsm8k, humaneval, medmcqa, mmlu, muse, rwku, safedialbench (ST:src/safetune/instrumentation/evaluate/suite/benchmarks.py:52-246). StrongREJECT is only a dataset-table entry (`walledai/StrongREJECT`, ST:src/safetune/data/dataset_ids.py:100), with no `evaluate()` judge. No multilingual benchmark; `examples/data/refusal_probes_demo.jsonl` has 8 probes in en/fr/es/hi.
- Own JSONL: `safetune.configure(datasets={"harmbench": "data/harm_en.jsonl", "advbench": "data/harm_hi.jsonl", "xstest": "data/xstest_en.jsonl"})`. Names are fixed, so remap them. Rows need a `prompt` column (or `prompt_col`); XSTest rows need `label` of `safe`/`unsafe` (ST:src/safetune/data/dataset_ids.py:12-27; ST:src/safetune/instrumentation/evaluate/suite/evaluate.py:318-327). Overriding `beavertails` or `alpaca` logs a deviation warning (ST:src/safetune/config.py:261-262, 298).
- CLI: `safetune eval --model ckpt --dataset harmbench,xstest --eval-backend hf` (ST:docs/reference/cli.md:42-53). `trainer.eval()` paths also run lm-eval utility tasks and are heavy.
- Defaults: greedy decoding, 512 new tokens, batch 8 (ST:src/safetune/config.py:187, 193). Eval fails loudly on a bad benchmark (`eval_strict`, ST:src/safetune/config.py:226).

## 6. Step 5: CuratorKIT

### 6a. Clean the synthetic SFT data
```
from curatorkit import Curator, CuratorConfig
r = Curator(CuratorConfig(dataset="data/bank_sft.jsonl", format="auto",
    dedup="minhash", minhash_threshold=0.85, clean=True, min_tokens=3,
    secrets_gate=True, pii_pseudonymize=True, pii_entity_types=[], toxicity_gate=True,
    toxicity_detoxify_model="multilingual", export_formats=["messages"], output_split={"train":0.95,"validation":0.05},
    output_dir="out/clean")).run(); r.print_summary()
```
(CU:docs/reference/configuration.md:15, 54-55, 67, 82-109, 118.) CLI: `curatorkit run pipeline.yaml` (CU:README.md:92-143).
- Input: JSONL (also JSON, CSV, Parquet, HF, PDF) with auto-detected Alpaca, ShareGPT or `messages` columns; `field_mapping={"your_col":"instruction"}` otherwise (CU:docs/guides/data-sources.md:9-16, 20-41, 70-72).
- Output: `sft_messages.jsonl` (chat `messages`), `sft_alpaca.jsonl`, `sft_sharegpt.jsonl`, plus `manifest.json`, `rejected.jsonl`, `lexsi_provenance.json`, `checksums.txt`; the folder loads with `load_dataset("out/clean", "sft_messages")` (CU:README.md:188-206; CU:docs/guides/exporters.md:16-24). Alpaca skips multi-turn rows; use `messages` or `sharegpt` (CU:docs/guides/exporters.md:36-46). Hand-off: `trainer.train("out/clean", dataset_config="sft_messages")` (ST:docs/user-guide/harden.md:37-46).
- Gates: exact and MinHash dedup (default `exact`, `minhash_threshold` 0.85), TextCleaner (`strip_html` deletes `<tags>`; turn off for red-team text) (CU:docs/reference/configuration.md:54-55, 67), `SecretsGate`, `PIIPseudonymizer`, `ToxicityGate`, then optional `RewardGate`, `DiversityGate`, `HallucinationGate` (needs a source in `input`; rows without one pass silently, CU:docs/guides/quality-gates.md:55). Fixed hygiene order: secrets, PII, toxicity.
- Language limits: PII uses Presidio with spaCy `en_core_web_lg` by default; default types are 8 (code adds `US_BANK_NUMBER`, docs list 7) and an unknown type such as `IN_PAN` is replaced by the literal `[IN_PAN]` (CU:curatorkit/hygiene/pii.py:62-71, 192-215). Indian IDs (PAN, Aadhaar) are not in the default list; adding `IN_PAN` or `IN_AADHAAR` depends on Presidio recognizers, untested here. `pii_language` exists in code but not in the reference table (CU:curatorkit/curator.py:460); Hindi PII needs the `stanza` or transformers engine, untested. Detoxify `multilingual` is the only non-English option; its Hindi coverage is not documented in CU (check Detoxify). Diversity and embedding dedup default to English `all-MiniLM-L6-v2`; set `embedding_model` to a multilingual encoder (CU:docs/reference/configuration.md:373).
- A failed LLM judge call rejects the sample (`judge_error:<type>`); `judge_on_error="pass"` keeps it (CU:docs/reference/configuration.md:174).

### 6b. Grounded QA from RBI FAQ pages
- No web or HTML connector (CU:docs/guides/data-sources.md:9-16; planned, CU:docs/community/roadmap.md:11). Fetch and chunk pages yourself, then write JSONL `{"text": "...", "source_url": "..."}`. With `format="pretrain"` and `field_mapping={"text":"output"}` each row becomes a `language_modeling` chunk, which the QA task grounds on (CU:curatorkit/connectors/base.py:670-679; CU:docs/guides/generation.md:9-15). PDF route needs `[pdf]` (MinerU, AGPL-3.0, CU:docs/getting-started/installation.md:39-41).
```
Curator(CuratorConfig(dataset="data/rbi_chunks.jsonl", format="pretrain", field_mapping={"text":"output"},
   generation_task="qa", num_questions=3, llm_model="openai/gpt-4o-mini", judge_llm_model="<different model>",
   hallucination_threshold=0.7, reward_threshold=0.7, diversity_threshold=0.92, export_formats=["messages"],
   output_dir="out/rbi_qa")).run()
```
- Output fields: `instruction`=question, `input`=source passage, `output`=answer (CU:docs/guides/generation.md:40); the gate checks the answer against that exact chunk. Use a different judge from the generator to avoid self-leniency (CU:docs/guides/quality-gates.md:60). For Hindi QA set `qa_prompt_template` (needs `{context}` and `{num_questions}`, CU:docs/reference/configuration.md:310).
- Check RBI's reuse terms yourself; CU's license forbids processing protected data without authorization (CU:LICENSE.md:46).

## 7. LLM backends and keys

| Lib | Generation and judging backends | Keys |
|---|---|---|
| CU | LiteLLM (any provider, `litellm>=1.60`) and a native Ollama client; local vLLM or `transformers serve` through `llm_api_base`; no in-process HF/vLLM client (CU:pyproject.toml:90-94; CU:curatorkit/llm/; CU:README.md:146-173) | provider env vars (`OPENAI_API_KEY`, `COHERE_API_KEY`, ...) or `llm_api_key`; `hf_token` for gated datasets (CU:docs/reference/configuration.md:19, 151) |
| CU judge | separate `judge_llm_model`, `judge_llm_api_base`, per-role `LLMOverride` (CU:docs/reference/configuration.md:167-195) | same |
| AK | `openai:`, `anthropic:`, `hf:`, `vllm:`, `litellm:`, `api:` (any OpenAI-compatible URL), `groq:`, `openrouter:`, `lexsi:`, callables (AK:docs/model_backends.md:5-25) | `OPENAI_API_KEY` is used only for api.openai.com; a custom `api_base` needs `api_key=` or `API_KEY` (AK:src/auditkit/model/api_gen.py:168-171, 209-215); `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `HF_TOKEN` |
| ST | local HF judges loaded in-process; vLLM if installed; `OpenAIJudge` over HTTP (ST:src/safetune/config.py:183, 255) | `HF_TOKEN`; `SAFETUNE_EVAL_BACKEND`, `SAFETUNE_GPU_MEM`, `SAFETUNE_EVAL_LIMIT`; `OPENAI_API_KEY` (or `api_key_env`) for `OpenAIJudge` (ST:src/safetune/core/eval/pipeline/scorer.py:388-392) |
| CK | local only | `HF_TOKEN`; `CUDA_HOME`, `TORCH_CUDA_ARCH_LIST` for quanto qint4 |

## 8. Licenses (summary, not legal advice)

- SafeTune, CircuitKIT, AuditKIT: Lexsi Labs Source Available License (LSAL) v1.2, not OSI-open.
  - Allowed free: personal research, academic research, teaching and publication, including papers, benchmarks and reproducibility artifacts; modify and redistribute with notice, license and Section 4 attached (ST:LICENSE.md:13-20).
  - An organization (company, charity, school, agency) using it for internal evaluation, red-teaming, safety auditing or repairing its own models needs prior written permission or a written acknowledgement to support@lexsi.ai (ST:LICENSE.md:24-35; CK:LICENSE.md:24-35; AK:LICENSE.md:24-35). Do this if the team enters as an organization.
  - Not allowed without a commercial license: selling a product or service whose value comes substantially from the library, SaaS/API, embedding in revenue software, paid consulting on it; modified copies must be marked modified, no relicensing or rebranding, no use of Lexsi or product names beyond unmodified copies (ST:LICENSE.md:37-45).
  - ST Section 4: no deploying a drifted or safety-degraded checkpoint, or any derivative not repaired and re-evaluated, in a production, user-facing or agentic system; no producing harmful model behavior outside research, evaluation or audit (ST:LICENSE.md:51-56). Section 4A: the base model's license applies to derived checkpoints (ST:LICENSE.md:58-60).
  - CK Section 4: no using it to locate, remove or weaken safety behavior in order to deploy the result; no deploying an exported checkpoint without re-evaluating safety (CK:LICENSE.md:51-57).
  - Nothing in LSAL claims ownership of your outputs (ownership clause covers the Licensed Work only, ST:LICENSE.md:62-64). My reading: publishing repaired and drifted checkpoints for research is allowed, deploying the drifted one is not. Label drifted checkpoints "research only, do not deploy".
- CuratorKIT: LSAL v1.1. Noncommercial includes internal evaluation and non-revenue use by nonprofits, schools and agencies; no Section 1A acknowledgement. Section 4 bans curating data to cause harmful behavior (except bona fide research with safeguards), processing protected or private data without authorization, and deploying models trained that way (CU:LICENSE.md:15-20, 41-47).
- Base and data licenses that propagate: tiny-aya-global/base are CC-BY-NC-4.0 (HF API), so any derived or quantized model is non-commercial and carries Cohere's terms. BeaverTails and Alpaca are CC-BY-NC-4.0 (HF API); ST pulls them for steering calibration and harden fallbacks when you pass no prompts (ST:src/safetune/runner/utils/data_utils.py:402-436). Avoid them or note the NC flow-through. WildGuard Apache-2.0, HarmBench classifier MIT.

## 9. Tiny Aya / cohere2 notes (collected)

- 3.35B, 36 layers, d_model 2048, 16/4 GQA heads, sliding-window plus NoPE full-attention layers, parallel attn+MLP block, tied 262k-vocab embeddings (CK:docs/advanced/tiny-aya.md:46-62).
- Chat template adds ~366 tokens of system preamble: set `max_len` from the template or leave it unset (ST:README.md:253-256; ST:CHANGELOG.md:212-217). Cohere ships named templates (`default`); AK fixed `vllm:` ignoring them and the double BOS (AK:CHANGELOG.md:260-265).
- ST: steering layer 24 of 36, alpha 0.25 for ReSta, MPS fp32 load path loads on CPU then moves (ST:src/safetune/runner/utils/model_utils.py:69-75), `pip uninstall -y torchao` on Colab (ST:README.md:257).
- ST loads cohere2 with `AutoModelForCausalLM`; only `aya_vision`/`cohere_compass` take the image-text class (ST:src/safetune/_refusal_helpers.py:64-98).
- CK needs `CohereTokenizer` (ships with transformers) and rejects vision checkpoints (CK:src/circuitkit/quick.py:136-155).
- vLLM serves cohere2 through its Command-R class (AK:docs/model_backends.md:165-168).

## 10. Risks / unknowns

1. Quantization on Tiny Aya is unvalidated. CK's authors never ran quanto `quantize()/freeze()` on a Cohere model; only module-name resolution was checked (CK:src/circuitkit/applications/arch_registry.py:161-166). The llmcompressor path was verified on 0.10.0.2 with transformers 4.57.6 only (CK:ENVIRONMENT.md:52-53); 0.15.0 is the release I confirmed allows transformers 5.15-5.21 (PyPI); I did not check 0.11 to 0.14. Expect to debug.
2. "Circuit-aware" means layer-level: whole layers stay bf16. Components found by ST (heads, neurons) can only be used as layer scores. Effective compression is lower than the nominal bits (embedding stays bf16, protected layers stay bf16).
3. Quanto output is not directly servable; the dequantized export is fake-quant bf16. Use llmcompressor for real 3/4-bit weights. vLLM loading of a Tiny Aya compressed-tensors checkpoint is untested.
4. No Hindi-capable judge or benchmark ships anywhere. WildGuard, Llama Guard, HarmBench classifier are English-trained and Hindi validity is unknown. WildGuard counts non-refusal as compliance. Plan: LLM judge with Hindi prompt plus a hand-labelled Hindi subset to measure judge agreement.
5. SafeGrad/Lisa default safety data is 6 English pairs; RefusalDirection sweep reads English refusal strings; steering calibration defaults to BeaverTails/Alpaca. All three need your own EN+HI data.
6. Steering strength and RESTA alpha are model-specific; defaults (20 and 1.0) break Tiny Aya. LoX defaults gave small gains in ST's own test (ST:src/safetune/runner/recover/_low_rank.py:18-24).
7. RESTA's safety vector `aligned - base` assumes tiny-aya-global was post-trained from tiny-aya-base; I did not check Cohere's model card for that. ST claims Tiny Aya support (ST:README.md:262-265), but its Cohere tests use random tiny configs, not real weights (ST:tests/runtime/test_hackathon_cohere_fixes.py:1-2); the alpha sweep numbers are the authors' and no script for them is in the repo. The vector is large: alpha 1.0 breaks the model.
8. Env: two environments needed if vLLM is used; CK import-order rule; transformers pin band; CK ENVIRONMENT.md contradicts pyproject. Pin library commits in the paper: ST changed DARE defaults (ST:CHANGELOG.md:41-47) and judge decoding and truncation (ST:CHANGELOG.md:64-68), both under [Unreleased].
9. EAP-IG and `ck.discover` on a 366-token preamble: memory and runtime are not documented for Tiny Aya; ST's own EAP `max_seq_len` default 64 is wrong for it. Refusal and compliance answer tokens unverified for the Cohere tokenizer.
10. ST data loader pads every row to one length from the first 32 rows and trains on the last assistant turn only; check this against the banking chat format.
11. CU: no web connector; English-centric PII and toxicity; docs and code disagree on the default PII types; `pii_language` undocumented; Hindi QA depends on the generator model's Hindi.
12. AK Tiny Aya Hindi answer changes with GPU and transformers version (AK:docs/model_backends.md:109-111): pin versions and report hardware, otherwise Hindi results will not reproduce.
13. ST CLI doc for `patch` omits `--aligned`; README version badge (0.1.8) and ReSta doc ("releases up to 0.1.14", ST:docs/user-guide/recover/layer/resta.md:61) disagree with pyproject 0.1.12. Treat docs as approximate; trust code.
14. Verified-by-reading only: nothing here was executed, so signatures and defaults reflect the cloned commits, not behavior on your GPUs.
