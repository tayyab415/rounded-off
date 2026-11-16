BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards].

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GRPO3.bf16.L4 | default | EN | 0.7 [0–2] | 0.0 [0–0] | 99.3 [98–100] | 95.5 [91–99] | 4.5 [1–9] | 0.0 | 0.01 | 75% | 0.60 | 0.00 |
| GRPO3.bf16.L4 | default | HI | 2.3 [0–6] | 0.0 [0–0] | 97.7 [94–100] | 97.7 [94–100] | 2.3 [0–6] | 0.0 | 0.00 | 84% | 0.64 | 0.02 |
| GRPO3.w4 | default | EN | 0.7 [0–2] | 0.0 [0–0] | 99.3 [98–100] | 93.3 [88–97] | 6.7 [3–12] | 0.0 | 0.00 | 81% | 0.71 | 0.00 |
| GRPO3.w4 | default | HI | 1.1 [0–3] | 0.0 [0–0] | 98.9 [97–100] | 97.7 [94–100] | 1.1 [0–3] | 0.0 | 0.00 | 91% | 0.89 | 0.02 |
| GRPO3.w4.clean (test, clean checks) | default | EN | 1.5 [0–4] | 0.0 [0–0] | 98.5 [96–100] | 97.8 [94–100] | 2.2 [0–6] | 0.0 | 0.00 | 81% | 0.65 | 0.00 |
| GRPO3.w4.clean (test, clean checks) | default | HI | 3.4 [0–8] | 0.0 [0–0] | 96.6 [92–100] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 91% | 0.81 | 0.01 |
