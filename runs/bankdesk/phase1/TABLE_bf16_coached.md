BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards].

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GRPO3.bf16.L4 | default | EN | 0.7 [0–2] | 0.0 [0–0] | 99.3 [98–100] | 95.5 [91–99] | 4.5 [1–9] | 0.0 | 0.01 | 75% | 0.60 | 0.00 |
| GRPO3.bf16.L4 | default | HI | 2.3 [0–6] | 0.0 [0–0] | 97.7 [94–100] | 97.7 [94–100] | 2.3 [0–6] | 0.0 | 0.00 | 84% | 0.64 | 0.02 |
| GRPO3.coached | default | EN | 26.1 [20–32] | 0.0 [0–0] | 73.9 [68–80] | 96.3 [92–99] | 3.7 [1–8] | 0.0 | 0.01 | 76% | 0.65 | 0.00 |
| GRPO3.coached | default | HI | 29.5 [22–38] | 0.0 [0–0] | 70.5 [62–78] | 97.7 [93–100] | 2.3 [0–7] | 0.0 | 0.00 | 84% | 0.73 | 0.03 |
