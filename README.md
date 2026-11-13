# Rounded Off: do safety repairs survive 4-bit?

Lexsi Labs AI Safety & Alignment Hackathon (Nov 2026), Track 2b. Tayyab Khan.

We fine-tune Cohere's Tiny Aya Global (3.35B) into an English + Hindi bank support assistant, measure what the fine-tune
does to safety, repair it with SafeTune, and check whether each repair survives 4-bit and 3-bit quantization, with
CircuitKIT for circuit discovery, CuratorKIT for data cleaning and AuditKIT as the release gate.

Write-up: `article/ARTICLE.md` (the Hugging Face article is the canonical version). Status and decisions: `PLAN.md`.

## Layout
- `scripts/` every step, in order (see "Reproduce").
- `data/eval/` evaluation prompts (public benchmarks + Adaption-generated bank sets). RBI FAQ text is not redistributed:
  `scripts/fetch_rbi.py` rebuilds it from rbi.org.in, and `scripts/build_data.py` builds the paired RBI eval.
- `data/sft_raw.jsonl` bank fine-tuning rows before CuratorKIT (Banking77 questions + Adaption answers).
- `results/` tables, gate reports, weight-change survival, CircuitKIT layer ranks, CuratorKIT recall, ROI.

## Reproduce (one NVIDIA L4, 24 GB)
Two Python 3.12 environments (`scripts/vm_bootstrap.sh`): env A = SafeTune + CircuitKIT + AuditKIT + CuratorKIT
(transformers 5.20.2, torch 2.14.1, llmcompressor 0.15.0); env B = vLLM 0.33.0. Library commits: SafeTune cc3de5f,
CircuitKIT 6e9782b, AuditKIT 556eb48, CuratorKIT ed45ae3.
1. Data: `build_public_sets.py`, `build_hi_sets.py`, `fetch_rbi.py`, `build_data.py`, `build_bank_sets.py`, `build_refusals.py`, `curate_sft.py`, `build_contaminated.py`.
2. Train: `train_harden.py --method plainsft|safegrad`.
3. Repair: `repair.py --method resta|wiseft|lox`.
4. Circuit: `ck_discover_refusal.py`.
5. Evaluate: `eval_batch.sh` (quantizes with `quant_rtn.py`, generates with `gen_vllm.py`, judges with `judge_guard.py` and `judge_behavior.py`).
6. Report: `make_tables.py`, `ak_gate.py`, `delta_survival.py`, `roi.py`.

## Licenses
Code: MIT. Derived models inherit Tiny Aya's CC-BY-NC-4.0. Lexsi libraries are under the Lexsi Source Available License.
