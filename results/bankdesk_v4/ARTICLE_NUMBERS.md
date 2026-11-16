# Numbers for article section 7.10

GRPO3, test split (444 episodes, `results/raw/hf_runs/bankdesk/e374042/GRPO3.default.jsonl`):
- 20 distinct tool sequences; the five most common cover 85.4%.
- At most 2 questions in any episode.
- Ambiguous cases questioned: genuine 72.1%, scam 98.2%.
- English questions about who asked or how they were contacted: 93.7% of 159.

| ambiguous cases | questioned % | n |
|---|---|---|
| amount: Rs 20,000 to 50,000 (genuine) | 72.7 | 33 |
| amount: Rs 20,000 to 50,000 (scam) | 100.0 | 33 |
| amount: over Rs 50,000 (genuine) | 73.3 | 15 |
| amount: over Rs 50,000 (scam) | 100.0 | 15 |
| amount: under Rs 20,000 (genuine) | 71.4 | 63 |
| amount: under Rs 20,000 (scam) | 96.8 | 63 |
| checks: any flag (genuine) | 100.0 | 39 |
| checks: any flag (scam) | 100.0 | 100 |
| checks: no flag (genuine) | 56.9 | 72 |
| checks: no flag (scam) | 81.8 | 11 |

Keyword rule on the scam victim's two answers (who asked, how contacted), English cards:
- train (233 cards): scams caught 63.9%, genuine flagged 9.0%
- test (67 cards): scams caught 94.0%, genuine flagged 19.4%
- 'told to keep it secret: yes': scam 27.5%, genuine 0.0%

v4 simulator (generator `0a736c407c2b`, 10000 held-out worlds): see `results/bankdesk_v4/RULE1.md`.
