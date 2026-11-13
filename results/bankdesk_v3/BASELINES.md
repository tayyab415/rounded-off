BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards].

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 | default | EN | 88.8 [81–95] | 0.0 [0–0] | 0.7 [0–2] | 78.4 [69–87] | 0.7 [0–2] | 5.6 | 0.03 | 95% | 0.00 | 0.80 |
| M0 | default | HI | 90.9 [84–97] | 4.5 [0–10] | 1.1 [0–3] | 85.2 [75–93] | 0.0 [0–0] | 4.0 | 0.02 | 97% | 0.05 | 0.62 |
| R_wise50 | default | EN | 94.8 [90–99] | 0.0 [0–0] | 3.0 [0–7] | 97.0 [93–100] | 1.5 [0–4] | 1.1 | 0.00 | 89% | 0.03 | 0.12 |
| R_wise50 | default | HI | 83.0 [75–91] | 0.0 [0–0] | 2.3 [0–6] | 79.5 [70–89] | 0.0 [0–0] | 4.5 | 0.26 | 94% | 0.08 | 1.15 |
| R_wise50 | strong | EN | 91.0 [85–96] | 0.0 [0–0] | 7.5 [3–13] | 97.8 [95–100] | 0.7 [0–2] | 0.4 | 0.01 | 100% | 0.01 | 0.11 |
| R_wise50 | strong | HI | 80.7 [70–91] | 1.1 [0–3] | 9.1 [2–17] | 86.4 [77–94] | 2.3 [0–6] | 2.8 | 0.15 | 96% | 0.13 | 0.74 |
| R_wise50.w4 | default | EN | 82.1 [75–89] | 1.5 [0–4] | 2.2 [0–5] | 81.3 [73–89] | 0.0 [0–0] | 2.2 | 0.05 | 89% | 0.28 | 0.72 |
| R_wise50.w4 | default | HI | 77.3 [67–88] | 4.5 [0–10] | 1.1 [0–3] | 72.7 [61–83] | 1.1 [0–3] | 4.5 | 0.27 | 89% | 0.24 | 1.16 |
