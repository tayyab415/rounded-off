BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards].

| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DSV4F | default | EN | 5.2 [1–9] | 0.0 [0–0] | 94.8 [91–99] | 73.9 [64–83] | 21.6 [13–31] | 0.7 | 0.06 | 97% | 0.81 | 0.01 |
| DSV4F | default | HI | 3.4 [0–8] | 0.0 [0–0] | 96.6 [92–100] | 80.7 [70–90] | 17.0 [8–27] | 0.6 | 0.01 | 100% | 0.90 | 0.03 |
| GLM53F | default | EN | 11.2 [7–16] | 0.0 [0–0] | 88.8 [84–93] | 70.9 [61–80] | 28.4 [19–38] | 0.4 | 0.00 | 98% | 0.08 | 0.03 |
| GLM53F | default | HI | 12.5 [7–19] | 0.0 [0–0] | 87.5 [81–93] | 75.0 [62–86] | 25.0 [14–38] | 0.0 | 0.00 | 96% | 0.14 | 0.09 |
