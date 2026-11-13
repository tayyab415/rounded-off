BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards]. Files: results/raw/hf_runs/bankdesk/e374042 (final job) plus results/raw/hf_runs/bankdesk/311e670 (R_wise50 test) and b381f32 (SFT3 test).

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DPO3 | default | EN | 3.7 [1–7] | 0.0 [0–0] | 96.3 [93–99] | 97.0 [93–100] | 3.0 [0–7] | 0.0 | 0.00 | 74% | 0.51 | 0.00 |
| DPO3 | default | HI | 5.7 [2–11] | 0.0 [0–0] | 94.3 [89–98] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 81% | 0.59 | 0.05 |
| GRPO3 | default | EN | 0.7 [0–2] | 0.0 [0–0] | 99.3 [98–100] | 96.3 [91–100] | 3.7 [0–9] | 0.0 | 0.01 | 75% | 0.59 | 0.00 |
| GRPO3 | default | HI | 2.3 [0–6] | 0.0 [0–0] | 97.7 [94–100] | 97.7 [93–100] | 2.3 [0–7] | 0.0 | 0.00 | 84% | 0.64 | 0.02 |
| R_wise50 | default | EN | 94.8 [90–99] | 0.0 [0–0] | 3.0 [0–7] | 97.0 [93–100] | 1.5 [0–4] | 1.1 | 0.00 | 89% | 0.03 | 0.12 |
| R_wise50 | default | HI | 83.0 [75–91] | 0.0 [0–0] | 2.3 [0–6] | 79.5 [70–89] | 0.0 [0–0] | 4.5 | 0.26 | 94% | 0.08 | 1.15 |
| SFT3 | default | EN | 6.0 [2–10] | 0.0 [0–0] | 94.0 [90–98] | 96.3 [92–99] | 3.7 [1–8] | 0.0 | 0.01 | 74% | 0.33 | 0.00 |
| SFT3 | default | HI | 5.7 [2–11] | 0.0 [0–0] | 94.3 [89–98] | 98.9 [97–100] | 1.1 [0–3] | 0.0 | 0.00 | 82% | 0.43 | 0.02 |
