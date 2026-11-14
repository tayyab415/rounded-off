# Safe on the benchmark, open for fraud

Lexsi Labs AI Safety & Alignment Hackathon (Nov 2026), Track 2b. Tayyab Khan. Project name: Rounded Off.

We fine-tune Cohere's Tiny Aya Global (3.35B) into an English + Hindi bank support assistant, repair its safety with
SafeTune, quantize it to 4-bit and 3-bit, and test every version on two red-teams side by side: HarmBench (generic) and
our own bank red-team (card testing, OTP phishing, false chargebacks, mule accounts, cash structuring). The repairs fix
the generic benchmark much more than the bank set, and rounding never undoes them. CuratorKIT cleans the data,
CircuitKIT finds the refusal layers, AuditKIT grades every compressed model against its parent.

The second half is **BankDesk**, an agent environment for the other side of bank fraud: coached scam victims who move
the money themselves. The model gets a simulated account and nine tools (ask the customer, verify a payee, check the
session, add a payee, raise a UPI limit, break an FD, transfer, escalate, reply), an LLM customer answers from hidden
facts, and code scores where the money went. The repaired bank model pays the scammer in 95% (EN) and 83% (HI) of
held-out scam cases. SFT on teacher demonstrations brings that to about 6%, and GRPO on pass-rate-filtered states to
0.7% / 2.3% while completing 96% / 98% of genuine tasks. With every bank check forced clean, 22% / 32% still get through.

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

## BankDesk

```bash
# run an agent on the 111 test cards with the LLM customer (GLM-5.3-Flash on Nebius; cached turns are replayed free)
python scripts/bankdesk_run.py --backend vllm:tyb343/rounded-off-bankdesk-grpo-v3 --tokenizer CohereLabs/tiny-aya-global \
  --cards data/bankdesk/cards_v3.jsonl --split test --customer llm --tag GRPO3 --out ep.jsonl   # add --signals clean for the stress test
python3 -I scripts/bankdesk_tables_v3.py table.md ep.jsonl          # money to scammer, genuine done, questions, with card-level CIs
python3 -m pytest tests/test_bankdesk.py                             # simulator and rubric tests
python3 scripts/bankdesk_transcripts.py ep.jsonl data/bankdesk/cards_v3.jsonl ep.md \
  --compare results/raw/bankdesk_final_GRPO3.default.jsonl          # readable tool-call transcripts, diffed against our run
```

`results/live_check/` is a re-run of GRPO3 on a fresh GPU with the command above (36 test episodes, the same 36 with
every check forced clean, and 8 from two hand-written cards). It gave the same outcome as our test run in all 72 test
episodes and the same tool sequence in 69 of 72; read `replay.md` to see each tool call and what the bank returned.

- Environment: `scripts/bankdesk.py` (tools, state, rubric), `scripts/bankdesk_customer.py` (LLM customer with cache),
  design in `notes/ENV_DESIGN.md`, review in `notes/SOL_REVIEW.md`. Cards and all training data:
  [tyb343/bankdesk-scenario-cards](https://huggingface.co/datasets/tyb343/bankdesk-scenario-cards).
- Fix, in order: `bankdesk_gen_cards.py` + `bankdesk_review_cards.py` (cards), `bankdesk_teacher.py` (demonstrations),
  `bankdesk_sft.py --bs 8 --accum 1`, `bankdesk_dpo.py`, `bankdesk_passrate.py --n 8` (keeps states whose 8 samples get
  different rewards), then `bankdesk_grpo.py` on those states (`--states`) with `--gens 8 --prompts-per-step 6
  --temperature 1.0 --epsilon-high 0.28 --beta 0 --loss-type dapo --lr 2e-5 --max-steps 100`. Exact calls: `PLAN.md`.
- We ran these on Hugging Face Jobs through `jobs/train_on_hf.py` and `jobs/run_on_hf.py`, launched only via
  `scripts/hf_budget.py`, which refuses a job that could push spend past the cap.
- Judges: `scripts/judge_harness.py` labels in batches of 12 to 18 with hidden hand-labelled anchors, a permutation
  re-check and a second-model jury (rubrics in `scripts/judge_rubrics.py`, sources in `notes/JUDGE_HARNESS.md`). Harmful
  sets never leave our GPU.

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
Bank red-team and borderline prompts, scam-victim sets and BankDesk cards: CC-BY-4.0. Teacher, customer and judge
models (GLM-5.3-Flash, DeepSeek-V4.1-Flash) are MIT.
