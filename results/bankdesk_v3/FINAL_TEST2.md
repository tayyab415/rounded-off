BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards]. Files: results/raw/hf_runs/bankdesk/e374042 (final job) plus results/raw/hf_runs/bankdesk/311e670 (R_wise50 test) and b381f32 (SFT3 test).

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DPO3 (test2) | default | EN | 3.6 [1–7] | 0.0 [0–0] | 96.4 [93–99] | 97.9 [95–100] | 0.0 [0–0] | 1.0 | 0.01 | 76% | 0.49 | 0.00 |
| DPO3 (test2) | default | HI | 5.4 [3–8] | 0.0 [0–0] | 94.6 [92–97] | 97.5 [95–99] | 1.1 [0–3] | 0.3 | 0.00 | 78% | 0.56 | 0.03 |
| GRPO3 (test2) | default | EN | 2.1 [1–4] | 0.0 [0–0] | 97.9 [96–99] | 99.0 [97–100] | 0.0 [0–0] | 0.5 | 0.01 | 77% | 0.56 | 0.00 |
| GRPO3 (test2) | default | HI | 1.4 [0–3] | 0.0 [0–0] | 98.3 [97–99] | 95.2 [93–97] | 4.2 [2–6] | 0.4 | 0.00 | 80% | 0.61 | 0.02 |
| R_wise50 (test2) | default | EN | 97.4 [94–100] | 0.0 [0–0] | 1.6 [0–4] | 98.4 [96–100] | 0.0 [0–0] | 1.0 | 0.00 | 99% | 0.00 | 0.05 |
| R_wise50 (test2) | default | HI | 76.6 [72–81] | 2.3 [1–4] | 1.4 [0–3] | 78.5 [74–83] | 0.3 [0–1] | 2.8 | 0.26 | 94% | 0.22 | 1.02 |
| SFT3 (test2) | default | EN | 6.2 [3–10] | 0.0 [0–0] | 93.8 [90–97] | 97.9 [95–100] | 0.0 [0–0] | 1.0 | 0.01 | 76% | 0.37 | 0.00 |
| SFT3 (test2) | default | HI | 4.2 [2–6] | 0.0 [0–0] | 95.8 [94–98] | 94.6 [92–97] | 4.2 [2–7] | 0.6 | 0.00 | 79% | 0.41 | 0.02 |
