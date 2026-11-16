# Rupee view of BankDesk v3 (illustrative)

This page turns the BankDesk test results into rupees. For each agent it adds up the money sent to the scammer's
account, then splits each loss between the customer, RBI and the two banks under RBI's revised rules. It is an
illustration of scale. The amounts are the task amounts on our scenario cards, not real fraud data.

What was counted:
- Test split of `data/bankdesk/cards_v3.jsonl`: 111 cards, 4 cases each, so 222 scam and 222 genuine requests per run
  (EN 134 + 134, HI 88 + 88).
- Agents: R_wise50 is the repaired bank chat model before any agent training. GRPO3 is the trained agent. R_any,
  R_two and R_narrow are bank rules that read the two bank checks and nothing else (see `RULES_BASELINE.md`).
- "Normal" checks are the noisy v3 bank checks. "Clean" forces every check to look fine, so only a question to the
  customer can reveal the scam. The two are separate rows.
- Model episodes use the LLM customer. Rule episodes never ask, so no customer is called.
- Each saved episode was replayed offline through `scripts/bankdesk.py` with the recorded customer answers. Every replay
  reproduced the saved outcome. A loss L is the total the agent sent to the scam payee in that episode.

How a loss is split. RBI's revised rules in force from 1 Jan 2027 (Commercial Banks Responsible Business Conduct
Third Amendment Directions 2026, paragraphs 4(15A), 76N and 76T; checked against the RBI text):
- A payment the customer approved under coercion is a fraudulent transaction caused by customer negligence (76N). The
  customer bears the loss, minus any 76T compensation.
- 76T: if L is Rs 50,000 or less, compensation is min(0.85 x L, Rs 25,000), once per lifetime, if the victim reports
  to the bank and to 1930 or the cybercrime portal within 5 calendar days.
- Below Rs 29,412, RBI pays 0.65 x L, the sending bank 0.10 x L and the beneficiary bank 0.10 x L. From Rs 29,412 to
  Rs 50,000, RBI pays Rs 19,118 and each bank Rs 2,941, which adds up to the Rs 25,000 cap.
- Above Rs 50,000 there is no 76T compensation. The customer bears all of it.

Assumptions: every loss is the victim's first claim, reported in time, and nothing is recovered. One scam request is
one victim.

Card amounts on the test split:
- EN: 67 cards, Rs 12,500 to Rs 150,000, median Rs 18,500, 6 above Rs 50,000
- HI: 44 cards, Rs 12,500 to Rs 150,000, median Rs 15,000, 9 above Rs 50,000

Losses above Rs 50,000 get no compensation, so the few large cards carry much of the customer's share. Rows with few
paid scams (the "paid" column) rest on one to three episodes. There are no confidence intervals here. The percentage
tables in `RULES_BASELINE.md` have them.

Files: `results/raw/hf_runs/bankdesk/311e670/R_wise50.default.jsonl`, `results/raw/hf_runs/bankdesk/e374042/R_wise50.default.clean.jsonl`, `results/raw/hf_runs/bankdesk/e374042/GRPO3.default.jsonl`, `results/raw/hf_runs/bankdesk/e374042/GRPO3.default.clean.jsonl`, `runs/bankdesk/rules/R_any.jsonl`, `runs/bankdesk/rules/R_any.clean.jsonl`, `runs/bankdesk/rules/R_two.jsonl`, `runs/bankdesk/rules/R_two.clean.jsonl`, `runs/bankdesk/rules/R_narrow.jsonl`, `runs/bankdesk/rules/R_narrow.clean.jsonl`.
Built by `python3 -I scripts/bankdesk_rupee_view.py --out results/bankdesk_v3/RUPEE_VIEW.md`.

## Per 1,000 scam requests: rupees sent to the scammer, and who carries them

All rupee columns are per 1,000 scam requests. "customer" + "RBI" + the two banks = "Rs lost".

| agent | checks | lang | paid / scam requests | Rs lost | customer | RBI | sending bank | beneficiary bank | paid scams over Rs 50,000 (count) |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| R_wise50 | normal | EN | 127 / 134 | 29,817,164 | 14,567,724 | 11,661,410 | 1,794,015 | 1,794,015 | 11 |
| R_wise50 | normal | HI | 73 / 88 | 35,102,273 | 24,181,818 | 8,351,000 | 1,284,727 | 1,284,727 | 14 |
| R_wise50 | normal | both | 200 / 222 | 31,912,162 | 18,378,716 | 10,349,176 | 1,592,135 | 1,592,135 | 25 |
| R_wise50 | clean | EN | 132 / 134 | 31,526,119 | 15,715,858 | 12,090,276 | 1,859,993 | 1,859,993 | 12 |
| R_wise50 | clean | HI | 68 / 88 | 28,539,773 | 17,740,057 | 8,258,670 | 1,270,523 | 1,270,523 | 10 |
| R_wise50 | clean | both | 200 / 222 | 30,342,342 | 16,518,243 | 10,571,441 | 1,626,329 | 1,626,329 | 22 |
| GRPO3 | normal | EN | 1 / 134 | 138,060 | 20,709 | 89,739 | 13,806 | 13,806 | 0 |
| GRPO3 | normal | HI | 2 / 88 | 738,636 | 309,659 | 328,045 | 50,466 | 50,466 | 0 |
| GRPO3 | normal | both | 3 / 222 | 376,126 | 135,248 | 184,203 | 28,338 | 28,338 | 0 |
| GRPO3 | clean | EN | 29 / 134 | 4,817,164 | 1,181,530 | 2,780,201 | 427,716 | 427,716 | 0 |
| GRPO3 | clean | HI | 28 / 88 | 11,051,136 | 6,061,080 | 3,815,966 | 587,045 | 587,045 | 3 |
| GRPO3 | clean | both | 57 / 222 | 7,288,288 | 3,115,766 | 3,190,775 | 490,874 | 490,874 | 3 |
| R_any | normal | EN | 16 / 134 | 3,141,791 | 1,549,627 | 1,217,537 | 187,313 | 187,313 | 2 |
| R_any | normal | HI | 6 / 88 | 1,704,545 | 556,818 | 877,682 | 135,023 | 135,023 | 0 |
| R_any | normal | both | 22 / 222 | 2,572,072 | 1,156,081 | 1,082,820 | 166,586 | 166,586 | 2 |
| R_any | clean | EN | 134 / 134 | 32,365,672 | 16,075,000 | 12,457,657 | 1,916,507 | 1,916,507 | 12 |
| R_any | clean | HI | 88 / 88 | 43,693,182 | 30,343,750 | 10,208,477 | 1,570,477 | 1,570,477 | 18 |
| R_any | clean | both | 222 / 222 | 36,855,856 | 21,731,081 | 11,566,090 | 1,779,342 | 1,779,342 | 30 |
| R_two | normal | EN | 48 / 134 | 11,492,537 | 5,511,194 | 4,574,000 | 703,672 | 703,672 | 4 |
| R_two | normal | HI | 32 / 88 | 14,431,818 | 9,829,545 | 3,519,409 | 541,432 | 541,432 | 6 |
| R_two | normal | both | 80 / 222 | 12,657,658 | 7,222,973 | 4,155,964 | 639,360 | 639,360 | 10 |
| R_two | clean | EN | 134 / 134 | 32,365,672 | 16,075,000 | 12,457,657 | 1,916,507 | 1,916,507 | 12 |
| R_two | clean | HI | 88 / 88 | 43,693,182 | 30,343,750 | 10,208,477 | 1,570,477 | 1,570,477 | 18 |
| R_two | clean | both | 222 / 222 | 36,855,856 | 21,731,081 | 11,566,090 | 1,779,342 | 1,779,342 | 30 |
| R_narrow | normal | EN | 66 / 134 | 14,335,821 | 6,198,881 | 6,222,403 | 957,269 | 957,269 | 4 |
| R_narrow | normal | HI | 46 / 88 | 20,681,818 | 13,215,909 | 5,709,273 | 878,318 | 878,318 | 6 |
| R_narrow | normal | both | 112 / 222 | 16,851,351 | 8,980,405 | 6,019,000 | 925,973 | 925,973 | 10 |
| R_narrow | clean | EN | 134 / 134 | 32,365,672 | 16,075,000 | 12,457,657 | 1,916,507 | 1,916,507 | 12 |
| R_narrow | clean | HI | 88 / 88 | 43,693,182 | 30,343,750 | 10,208,477 | 1,570,477 | 1,570,477 | 18 |
| R_narrow | clean | both | 222 / 222 | 36,855,856 | 21,731,081 | 11,566,090 | 1,779,342 | 1,779,342 | 30 |

## Per 1,000 genuine requests: customers blocked and tasks not done

"not done" counts every genuine request whose payment did not go through, blocked or not.

| agent | checks | lang | genuine requests | blocked (false escalation) | not done |
|---|---|---|---|---:|---:|
| R_wise50 | normal | EN | 134 | 15 | 30 |
| R_wise50 | normal | HI | 88 | 0 | 205 |
| R_wise50 | normal | both | 222 | 9 | 99 |
| R_wise50 | clean | EN | 134 | 0 | 15 |
| R_wise50 | clean | HI | 88 | 0 | 261 |
| R_wise50 | clean | both | 222 | 0 | 113 |
| GRPO3 | normal | EN | 134 | 37 | 37 |
| GRPO3 | normal | HI | 88 | 23 | 23 |
| GRPO3 | normal | both | 222 | 32 | 32 |
| GRPO3 | clean | EN | 134 | 52 | 52 |
| GRPO3 | clean | HI | 88 | 0 | 0 |
| GRPO3 | clean | both | 222 | 32 | 32 |
| R_any | normal | EN | 134 | 343 | 343 |
| R_any | normal | HI | 88 | 364 | 364 |
| R_any | normal | both | 222 | 351 | 351 |
| R_any | clean | EN | 134 | 0 | 0 |
| R_any | clean | HI | 88 | 0 | 0 |
| R_any | clean | both | 222 | 0 | 0 |
| R_two | normal | EN | 134 | 119 | 119 |
| R_two | normal | HI | 88 | 68 | 68 |
| R_two | normal | both | 222 | 99 | 99 |
| R_two | clean | EN | 134 | 0 | 0 |
| R_two | clean | HI | 88 | 0 | 0 |
| R_two | clean | both | 222 | 0 | 0 |
| R_narrow | normal | EN | 134 | 30 | 30 |
| R_narrow | normal | HI | 88 | 68 | 68 |
| R_narrow | normal | both | 222 | 45 | 45 |
| R_narrow | clean | EN | 134 | 0 | 0 |
| R_narrow | clean | HI | 88 | 0 | 0 |
| R_narrow | clean | both | 222 | 0 | 0 |
