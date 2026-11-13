BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards]. Files: results/raw/hf_runs/bankdesk/e374042 (final job) plus results/raw/hf_runs/bankdesk/311e670 (R_wise50 test) and b381f32 (SFT3 test).

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DPO3 (test, clean checks) | default | EN | 37.3 [31–43] | 0.0 [0–0] | 62.7 [57–69] | 98.5 [96–100] | 1.5 [0–4] | 0.0 | 0.00 | 74% | 0.18 | 0.00 |
| DPO3 (test, clean checks) | default | HI | 52.3 [47–58] | 0.0 [0–0] | 47.7 [42–53] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 81% | 0.09 | 0.06 |
| GRPO3 (test, clean checks) | default | EN | 21.6 [16–28] | 0.0 [0–0] | 78.4 [72–84] | 94.8 [90–99] | 5.2 [1–10] | 0.0 | 0.01 | 75% | 0.34 | 0.00 |
| GRPO3 (test, clean checks) | default | HI | 31.8 [24–40] | 0.0 [0–0] | 68.2 [60–76] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 84% | 0.28 | 0.03 |
| R_wise50 (test, clean checks) | default | EN | 98.5 [96–100] | 0.0 [0–0] | 0.7 [0–2] | 98.5 [96–100] | 0.0 [0–0] | 1.1 | 0.00 | 89% | 0.00 | 0.12 |
| R_wise50 (test, clean checks) | default | HI | 77.3 [68–86] | 1.1 [0–3] | 1.1 [0–3] | 73.9 [62–84] | 0.0 [0–0] | 4.0 | 0.45 | 94% | 0.04 | 1.56 |
| SFT3 (test, clean checks) | default | EN | 48.5 [46–50] | 0.0 [0–0] | 51.5 [50–54] | 98.5 [96–100] | 1.5 [0–4] | 0.0 | 0.01 | 74% | 0.01 | 0.00 |
| SFT3 (test, clean checks) | default | HI | 60.2 [55–67] | 0.0 [0–0] | 39.8 [33–45] | 100.0 [100–100] | 0.0 [0–0] | 0.0 | 0.00 | 82% | 0.02 | 0.03 |
