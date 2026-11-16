BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards].

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GRPO3.bf16.L4.clean (test, clean checks) | default | EN | 20.9 [15–27] | 0.0 [0–0] | 79.1 [73–85] | 97.0 [94–99] | 3.0 [1–6] | 0.0 | 0.01 | 75% | 0.33 | 0.00 |
| GRPO3.bf16.L4.clean (test, clean checks) | default | HI | 31.8 [24–40] | 0.0 [0–0] | 68.2 [60–76] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 84% | 0.27 | 0.03 |
| GRPO3.w3 | default | EN | 8.2 [4–13] | 0.0 [0–0] | 89.6 [84–94] | 94.0 [90–98] | 5.2 [1–10] | 0.4 | 0.05 | 64% | 0.99 | 0.04 |
| GRPO3.w3 | default | HI | 4.5 [0–10] | 2.3 [0–6] | 92.0 [85–98] | 94.3 [89–99] | 2.3 [0–6] | 0.6 | 0.00 | 70% | 1.21 | 0.14 |
| GRPO3.w3.clean (test, clean checks) | default | EN | 22.4 [16–29] | 0.0 [0–0] | 76.1 [69–82] | 97.8 [95–100] | 1.5 [0–4] | 0.0 | 0.02 | 64% | 0.79 | 0.04 |
| GRPO3.w3.clean (test, clean checks) | default | HI | 23.9 [16–33] | 3.4 [0–7] | 68.2 [58–77] | 95.5 [90–100] | 3.4 [0–9] | 0.6 | 0.00 | 70% | 1.03 | 0.13 |
| GRPO3.w4.clean (test, clean checks) | default | EN | 1.5 [0–4] | 0.0 [0–0] | 98.5 [96–100] | 97.8 [94–100] | 2.2 [0–6] | 0.0 | 0.00 | 81% | 0.65 | 0.00 |
| GRPO3.w4.clean (test, clean checks) | default | HI | 3.4 [0–8] | 0.0 [0–0] | 96.6 [92–100] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 91% | 0.81 | 0.01 |
