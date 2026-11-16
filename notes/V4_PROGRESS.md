# BankDesk v4: progress

Design: `notes/BANKDESK_V4_DESIGN.md`. Rules: `PLAN.md` (search "RULE V4"). Update this file at the end of each step.

## Done condition for v4

A Tiny Aya agent trained in v4, tested once on Adaption-written worlds at bf16, 4-bit and 3-bit, with the baselines
and measures of design section 7 in one table, and every rule in design sections 12.6 and 13.5 met or reported as missed.

## Steps

| # | Step | Status |
|---|---|---|
| 1 | Generator, exact posterior, reference policy, baselines, tests (CPU) | **done** 2026-11-16 01:57 IST: `scripts/bankdesk_v4.py`, `tests/test_bankdesk_v4.py` (12 tests), Rule V4-1 passes, `results/bankdesk_v4/RULE1.md` (hash `87dd17eaf9b0` at first, superseded in step 3) |
| 2 | Episode harness: case file in the first message, `lookup`, `request_details` (the form), `decide`, the bank's policy table, code reward, a finisher that only knows the case file (CPU) | **done** 2026-11-16 02:06 IST: `scripts/bankdesk_v4_env.py`, `tests/test_bankdesk_v4_env.py` (10 tests) |
| 3 | Evidence that only appears in the customer's words (`CUES`), and outside checks that exist only if the story names a company or number | **done** 2026-11-16 02:06 IST: generator re-frozen at hash `0a736c407c2b`, Rule V4-1 re-run and passes |
| 4 | Wording pilot (60 worlds, English, Hindi, Hinglish; writer and reviewer swap; round-trip check) | **done** 2026-11-16 03:00 IST: `scripts/bankdesk_v4_words.py`, Rule V4-3 passed after one prompt fix; 51 rows kept |
| 5 | Pilots with real models on 48 worlds: GLM (Nebius), GRPO3 and R_wise50 (Kaggle T4) | **done** 2026-11-16 03:00 IST: Rule V4-2 results in `PLAN.md`; syntax simplified under (c) |
| 6 | Harness v2: exact expected-value reward, safe default, refused lookups, soft targets, bare-name forms, policy table in the prompt | **done** 2026-11-16 03:00 IST: 44 tests pass |
| 7 | Training-data builder and trainer: `scripts/bankdesk_v4_data.py` (expert and DAgger rows from exact values), `scripts/bankdesk_v4_train.py` (one-epoch LoRA, last turn only), `scripts/kaggle_v4.py` (bundle, kernel, wait, fetch) | **done** 2026-11-16 03:00 IST; Kaggle speed probe running (`bankdesk-v4-probe`) |
| 8 | Wording at scale (train 600, dev 100, rl 500) with prompt v3 and the leak audit (Rule V4-4) | **done** 2026-11-16 06:44 IST: kept dev 98, train 474, rl 389; audit PASS; $2.21 |
| 9 | Round 0: SFT on expert rows (worded worlds), roll out on dev, pick by entropy and mixed-reward share | **done** 2026-11-16 06:44 IST: Rule V4-5 PASS but below the fixed form (+0.638 vs +0.667; forms in 100% of cases). Cause: tau 0.02 too soft |
| 10 | DAgger rounds 1 to 3: student plays fresh worlds, generator labels, retrain | round 1 running on Kaggle (`bankdesk-v4-r1`): tau 0.005 + 298 DAgger rows x2; Rule V4-6 |
| 11 | GRPO on AWS (exact-value reward; DeepSeek ranks tied best samples); DAgger alone reported next to DAgger + GRPO | script written (`scripts/bankdesk_v4_grpo.py`), checked locally; runs after 10 |
| 12 | Adaption test wording; dev gate at 4-bit; one test run at bf16, 4-bit, 3-bit with coached and shifted sets; chat gate | Adaption wording for test-0..299 running (Opus subagent, at most 120 credits) |
| 13 | Phase two: tailored field wording and messages from the GLM teacher; judge calibration on 40 hand labels | after 12 |

## AWS estimate (2026-11-16, from last night's run times at about $1 per GPU hour)

Agent only: about 16 GPU hours, $17 to $22 (pilot 1 h, setup 1.5 h, SFT 5 to 7 h, DPO and pass-rate 1.5 h, GRPO 2 to
2.5 h, dev gate and test and chat gate 4 h, one failed run allowed for). Redoing the bank chat fine-tune and repair
adds about $4. $3.70 is left under the $35 cap, so the ask is about $20 more (cap about $55). Not yet approved.

## Not built yet (known gaps in steps 2 and 3)

- `ask_customer` (one free-text follow-up) and `callback`: both need a likelihood in the generator first.
- Decision messages come from templates that name the two facts that moved the risk most. Field wording is the bank's standard question. Teacher-written wording is phase two.
- v4 work is uncommitted (another session has uncommitted edits to tracked files on master; I did not switch branches under it).
- Abandonment and the effect of a delay enter the reward as expected values; no episode ends with "customer left".
- The opening message is an English template. Hindi and Hinglish arrive with the real wording in step 4.
- The secret-word check is a regex (English and Hindi). The judge rubric should back it up.
- The policy table comes out the same for all three stakes at the current four risk bands.

## Notes for the next session

- The generator's difficulty is set by `SHARP` in `scripts/bankdesk_v4.py` (one knob per evidence layer). Changing
  any rate changes the hash; rerun `python3 scripts/bankdesk_v4.py rule1 --n 20000 --out results/bankdesk_v4/RULE1.md`.
- "Reference policy" means exact posterior plus greedy planning. Do not call it optimal.
- No delay, callback or warning effect on the victim is modelled yet beyond "a delay stops 60% of scams". That
  number is a design guess.
- Nothing is committed. Another session has uncommitted edits to the article, README and v3 scripts.
