# Safe on the benchmark, open for fraud

Lexsi Labs AI Safety & Alignment Hackathon (Nov 2026), Track 2b. Tayyab Khan. Project name: Rounded Off.

We fine-tune Cohere's Tiny Aya Global (3.35B) into an English + Hindi bank support assistant, repair its safety with
SafeTune, quantize it to 4-bit and 3-bit, and test every version on two red-teams side by side: HarmBench (generic) and
our own bank red-team (card testing, OTP phishing, false chargebacks, mule accounts, cash structuring). The repairs fix
the generic benchmark much more than the bank set, and rounding never undoes them. CuratorKIT cleans the data,
CircuitKIT finds the refusal layers, AuditKIT grades every compressed model against its parent.

Write-up: `article/ARTICLE.md` (the Hugging Face article is the canonical version). Status and decisions: `PLAN.md`.

## Bank release gate

One command, one 24 GB GPU, both Python envs below. Answers the bank red-team, borderline and task sets in English and
Hindi, runs both judges, prints a PASS / WARN / FAIL report card, exits 0 / 1 / 2.

```bash
bash scripts/bank_gate.sh my-org/bank-model --tag bank.bf16
bash scripts/bank_gate.sh my-org/bank-model --bits 4 --group 128 --tag bank.w4 --ref bank.bf16   # + task drop and AuditKIT grade
LIMIT=5 bash scripts/bank_gate.sh CohereLabs/tiny-aya-global --tag smoke                          # 5 prompts per set
```

Thresholds: `scripts/gate_thresholds.json` (our defaults, not a standard). Report from existing judged files:
`python scripts/gate_report.py JUDGED_DIR TAG [--ref TAG]`. Example reports: `results/gate/`.
The prompts alone: [tyb343/bank-redteam-en-hi](https://huggingface.co/datasets/tyb343/bank-redteam-en-hi).

## Layout
- `scripts/` every step, in order (see "Reproduce"). `scripts/runs/` the exact job scripts run on the VM, with run order.
- `data/eval/` evaluation prompts (public benchmarks + Adaption-generated bank sets). RBI FAQ text is not redistributed:
  `scripts/fetch_rbi.py` rebuilds it from rbi.org.in, and `scripts/build_data.py` builds the paired RBI eval.
- `data/sft_raw.jsonl` bank fine-tuning rows before CuratorKIT (Banking77 questions + Adaption answers).
- `results/` tables (`main_table_v3.csv` has every cell with its 95% interval), gate reports, weight-change survival,
  CircuitKIT layer ranks, CuratorKIT recall, ROI.

## Reproduce (one NVIDIA L4, 24 GB)
Two Python 3.12 environments (`scripts/vm_bootstrap.sh`): env A = SafeTune + CircuitKIT + AuditKIT + CuratorKIT
(transformers 5.20.2, torch 2.14.1, llmcompressor 0.15.0); env B = vLLM 0.33.0. Library commits: SafeTune cc3de5f,
CircuitKIT 6e9782b, AuditKIT 556eb48, CuratorKIT ed45ae3. Every fine-tune uses seed 13; decoding is greedy.
1. Data: `build_public_sets.py`, `build_hi_sets.py`, `fetch_rbi.py`, `build_data.py`, `build_bank_sets.py`, `build_refusals.py`, `curate_sft.py`, `build_contaminated.py`.
2. Train: `train_harden.py --method plainsft|safegrad`.
3. Repair: `repair.py --method resta|wiseft|lox`; pick the setting with `select_repair.py` (rule fixed before any quantized result).
4. Circuit: `ck_discover_refusal.py`.
5. Evaluate: `eval_batch.sh` (quantizes with `quant_rtn.py`, generates with `gen_vllm.py`, judges with `judge_guard.py` and `judge_behavior.py`). Closed-model reference: `api_reference.py` (Amazon Bedrock).
6. Report: `make_tables.py`, `article_tables.py`, `plot_headline.py`, `gate_report.py`, `ak_gate.py`, `delta_survival.py`, `roi.py`.

Raw model answers are not in the repo (they include harmful completions).

## Licenses
Code: MIT. Derived models inherit Tiny Aya's CC-BY-NC-4.0. Lexsi libraries are under the Lexsi Source Available License.
Bank red-team and borderline prompts: CC-BY-4.0.
