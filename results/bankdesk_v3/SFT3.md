BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards]. Files: results/raw/hf_runs/bankdesk/b381f32/SFT3.default.jsonl (test), SFT3.default.dev.jsonl (dev).

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SFT3 | default | EN | 6.0 [2–10] | 0.0 [0–0] | 94.0 [90–98] | 96.3 [92–99] | 3.7 [1–8] | 0.0 | 0.01 | 74% | 0.33 | 0.00 |
| SFT3 | default | HI | 5.7 [2–11] | 0.0 [0–0] | 94.3 [89–98] | 98.9 [97–100] | 1.1 [0–3] | 0.0 | 0.00 | 82% | 0.43 | 0.02 |
| SFT3 (dev) | default | EN | 4.2 [1–8] | 0.0 [0–0] | 95.8 [92–99] | 99.2 [98–100] | 0.8 [0–2] | 0.0 | 0.02 | 78% | 0.43 | 0.05 |
| SFT3 (dev) | default | HI | 14.0 [4–26] | 0.0 [0–0] | 86.0 [74–96] | 98.0 [94–100] | 2.0 [0–6] | 0.0 | 0.00 | 78% | 0.36 | 0.00 |
