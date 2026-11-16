# Bank rules baseline for BankDesk v3

Why use a model at all? A bank could run fixed rules on its own checks instead. This page plays three such rules
through the same harness, on the same 111 test cards, and sets them next to R_wise50 (the repaired bank chat model,
before any agent training) and GRPO3 (the trained agent).

Each rule episode makes the two check calls any agent can make: `verify_payee` on the payee account the customer
shared, then `check_session`. The rule reads the two `[Bank check]` lines the harness prints and counts six flags:
- name mismatch
- account opened less than 30 days ago
- 10 or more incoming transfers in the last 24 hours
- customer on a phone call
- screen-sharing app
- new device

The script checks that the flags it reads from the printed text equal the simulator's own values, case by case. The
rules:
- R_any holds and escalates if any flag is up.
- R_two holds if two or more flags are up.
- R_narrow holds only for a screen-sharing app, a name mismatch, or a phone call while paying an account under 30 days
  old.

A rule that does not hold completes the task with the harness's own task steps (`_task_steps` in
`scripts/bankdesk.py`). Rules never ask the customer and never read the customer's message. The agent can do both, on
top of the same two checks. A rule gives the same result on the ambiguous and the clear case of a card, because the
simulator gives both the same checks.

Setup:
- Test split of `data/bankdesk/cards_v3.jsonl`: 111 cards (67 EN, 44 HI), 4 cases each, so 134 scam and 134 genuine
  cases in English and 88 of each in Hindi.
- Normal checks are the noisy v3 checks. Clean checks force every check to look fine (`--signals clean`), so only the
  customer's words can reveal a scam. They are separate rows.
- Model rows are the saved runs behind `FINAL_TEST.md` and `FINAL_CLEAN.md` (default prompt, LLM customer):
  `results/raw/hf_runs/bankdesk/e374042/GRPO3.default.jsonl`, `GRPO3.default.clean.jsonl`,
  `R_wise50.default.clean.jsonl`, and `results/raw/hf_runs/bankdesk/311e670/R_wise50.default.jsonl`. Each has 444
  episodes, all on test cards, the same case set as the rule runs. Their numbers match `FINAL_TEST.md` and
  `FINAL_CLEAN.md`.
- Rule rows call no customer. The "LLM customer" note in the `bankdesk_tables_v3.py` header applies to model rows
  only.
- How often the flags fire with normal checks: 9.9% of scam cases show no flag at all, and 35.1% of genuine cases show
  at least one.

Reproduce: `python3 -I scripts/bankdesk_rules_baseline.py`. It writes `runs/bankdesk/rules/{R_any,R_two,R_narrow}.jsonl`
and `.clean.jsonl`, then runs `bankdesk_tables_v3.py` over those six files plus the four model files into
`runs/bankdesk/rules/TABLE_v3.md`. The table below takes three columns of that output. The full output is at the end.

## Results

Percent of cases [95% CI, resampling whole cards]. Money to scammer is out of scam cases. Genuine done and false
escalation are out of genuine cases.

| agent | checks | lang | money to scammer ↓ | genuine done ↑ | false escalation ↓ |
|---|---|---|---|---|---|
| R_wise50 | normal | EN | 94.8 [90–99] | 97.0 [93–100] | 1.5 [0–4] |
| R_wise50 | normal | HI | 83.0 [75–91] | 79.5 [70–89] | 0.0 [0–0] |
| GRPO3 | normal | EN | 0.7 [0–2] | 96.3 [91–100] | 3.7 [0–9] |
| GRPO3 | normal | HI | 2.3 [0–6] | 97.7 [93–100] | 2.3 [0–7] |
| R_any | normal | EN | 11.9 [4–19] | 65.7 [54–78] | 34.3 [22–46] |
| R_any | normal | HI | 6.8 [0–16] | 63.6 [48–77] | 36.4 [23–52] |
| R_two | normal | EN | 35.8 [25–48] | 88.1 [81–96] | 11.9 [4–19] |
| R_two | normal | HI | 36.4 [23–50] | 93.2 [84–100] | 6.8 [0–16] |
| R_narrow | normal | EN | 49.3 [37–61] | 97.0 [93–100] | 3.0 [0–7] |
| R_narrow | normal | HI | 52.3 [39–66] | 93.2 [84–100] | 6.8 [0–16] |
| R_wise50 | clean | EN | 98.5 [96–100] | 98.5 [96–100] | 0.0 [0–0] |
| R_wise50 | clean | HI | 77.3 [68–86] | 73.9 [62–84] | 0.0 [0–0] |
| GRPO3 | clean | EN | 21.6 [16–28] | 94.8 [90–99] | 5.2 [1–10] |
| GRPO3 | clean | HI | 31.8 [24–40] | 100.0 [100–100] | 0.0 [0–0] |
| R_any | clean | EN | 100.0 [100–100] | 100.0 [100–100] | 0.0 [0–0] |
| R_any | clean | HI | 100.0 [100–100] | 100.0 [100–100] | 0.0 [0–0] |
| R_two | clean | EN | 100.0 [100–100] | 100.0 [100–100] | 0.0 [0–0] |
| R_two | clean | HI | 100.0 [100–100] | 100.0 [100–100] | 0.0 [0–0] |
| R_narrow | clean | EN | 100.0 [100–100] | 100.0 [100–100] | 0.0 [0–0] |
| R_narrow | clean | HI | 100.0 [100–100] | 100.0 [100–100] | 0.0 [0–0] |

## What it shows

With normal checks, each rule trades scams paid against genuine customers blocked. R_any lets 11.9% (EN) and 6.8%
(HI) of scams pay and blocks about one genuine customer in three; R_narrow blocks about as few as GRPO3 (3.0% / 6.8%)
but lets about half the scams pay. GRPO3 loses 0.7% / 2.3% while blocking 3.7% / 2.3%, though in Hindi its
money-to-scammer interval overlaps R_any's (2.3 [0–6] against 6.8 [0–16]). With clean checks no flag fires and every
rule pays every scammer, while GRPO3 still stops 58% (EN) and 45% (HI) of the ambiguous scams, where only a question
can reveal the story, and 99% / 91% of the clear ones. The check noise rates are our own design
(`notes/ENV_DESIGN.md`), so the size of the rules' trade-off is ours too; what should carry over is that a rule reading
only checks has nothing to go on when they look clean.

## All columns (`bankdesk_tables_v3.py` output)

BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl. Percent [95% CI, resampling cards]. Model
rows use the LLM customer (GLM-5.3-Flash); rule rows ("prompt" none) call no customer.

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GRPO3 | default | EN | 0.7 [0–2] | 0.0 [0–0] | 99.3 [98–100] | 96.3 [91–100] | 3.7 [0–9] | 0.0 | 0.01 | 75% | 0.59 | 0.00 |
| GRPO3 | default | HI | 2.3 [0–6] | 0.0 [0–0] | 97.7 [94–100] | 97.7 [93–100] | 2.3 [0–7] | 0.0 | 0.00 | 84% | 0.64 | 0.02 |
| GRPO3 (test, clean checks) | default | EN | 21.6 [16–28] | 0.0 [0–0] | 78.4 [72–84] | 94.8 [90–99] | 5.2 [1–10] | 0.0 | 0.01 | 75% | 0.34 | 0.00 |
| GRPO3 (test, clean checks) | default | HI | 31.8 [24–40] | 0.0 [0–0] | 68.2 [60–76] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 84% | 0.28 | 0.03 |
| R_any | none | EN | 11.9 [4–19] | 0.0 [0–0] | 88.1 [81–96] | 65.7 [54–78] | 34.3 [22–46] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_any | none | HI | 6.8 [0–16] | 0.0 [0–0] | 93.2 [84–100] | 63.6 [48–77] | 36.4 [23–52] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_any (test, clean checks) | none | EN | 100.0 [100–100] | 0.0 [0–0] | 0.0 [0–0] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_any (test, clean checks) | none | HI | 100.0 [100–100] | 0.0 [0–0] | 0.0 [0–0] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_narrow | none | EN | 49.3 [37–61] | 0.0 [0–0] | 50.7 [39–63] | 97.0 [93–100] | 3.0 [0–7] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_narrow | none | HI | 52.3 [39–66] | 0.0 [0–0] | 47.7 [34–61] | 93.2 [84–100] | 6.8 [0–16] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_narrow (test, clean checks) | none | EN | 100.0 [100–100] | 0.0 [0–0] | 0.0 [0–0] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_narrow (test, clean checks) | none | HI | 100.0 [100–100] | 0.0 [0–0] | 0.0 [0–0] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_two | none | EN | 35.8 [25–48] | 0.0 [0–0] | 64.2 [52–75] | 88.1 [81–96] | 11.9 [4–19] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_two | none | HI | 36.4 [23–50] | 0.0 [0–0] | 63.6 [50–77] | 93.2 [84–100] | 6.8 [0–16] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_two (test, clean checks) | none | EN | 100.0 [100–100] | 0.0 [0–0] | 0.0 [0–0] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_two (test, clean checks) | none | HI | 100.0 [100–100] | 0.0 [0–0] | 0.0 [0–0] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 100% | 0.00 | 0.00 |
| R_wise50 | default | EN | 94.8 [90–99] | 0.0 [0–0] | 3.0 [0–7] | 97.0 [93–100] | 1.5 [0–4] | 1.1 | 0.00 | 89% | 0.03 | 0.12 |
| R_wise50 | default | HI | 83.0 [75–91] | 0.0 [0–0] | 2.3 [0–6] | 79.5 [70–89] | 0.0 [0–0] | 4.5 | 0.26 | 94% | 0.08 | 1.15 |
| R_wise50 (test, clean checks) | default | EN | 98.5 [96–100] | 0.0 [0–0] | 0.7 [0–2] | 98.5 [96–100] | 0.0 [0–0] | 1.1 | 0.00 | 89% | 0.00 | 0.12 |
| R_wise50 (test, clean checks) | default | HI | 77.3 [68–86] | 1.1 [0–3] | 1.1 [0–3] | 73.9 [62–84] | 0.0 [0–0] | 4.0 | 0.45 | 94% | 0.04 | 1.56 |
