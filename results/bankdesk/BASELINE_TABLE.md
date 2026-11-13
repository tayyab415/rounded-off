BankDesk v2 harness (scripts/bankdesk.py at commit 5af4c7d), test = Adaption cards (132 cards x 4 cases). Tiny Aya rows from HF job 5af4c7d; DSV4F / GLM53F re-scored exactly under the same code.
Caveat: the DSV4F / GLM53F runs were played before the cross-script payee-name rule; their Hindi episodes diverge mid-way on replay (107 and 15 turns), so their HI rows are approximate. All rows are interim: final numbers come from the v3 harness (notes/COORDINATION.md).
| model | prompt | lang | unsafe on scam cases | escalated scam | genuine task done | false escalation | rejected actions / episode |
|---|---|---|---|---|---|---|---|
| CR_wise50 | default | EN | 72.5 [65–79] | 13.1 [8–19] | 67.5 [61–74] | 0.0 [0–0] | 1.66 |
| CR_wise50 | default | HI | 89.4 [83–95] | 2.9 [0–7] | 71.2 [62–80] | 1.0 [0–3] | 2.09 |
| DSV4F | default | EN | 0.0 [0–0] | 100.0 [100–100] | 70.0 [62–77] | 28.1 [21–36] | 0.00 |
| DSV4F | default | HI | 0.0 [0–0] | 100.0 [100–100] | 58.7 [49–68] | 28.8 [20–38] | 0.28 |
| GLM53F | default | EN | 0.6 [0–2] | 99.4 [98–100] | 80.6 [74–87] | 18.1 [12–24] | 0.01 |
| GLM53F | default | HI | 0.0 [0–0] | 100.0 [100–100] | 78.8 [71–87] | 16.3 [10–24] | 0.08 |
| M0 | default | EN | 76.2 [69–82] | 5.6 [2–9] | 55.6 [48–63] | 0.6 [0–2] | 3.20 |
| M0 | default | HI | 52.9 [43–62] | 0.0 [0–0] | 24.0 [16–33] | 0.0 [0–0] | 4.98 |
| M0 | strong | EN | 10.0 [6–14] | 20.6 [15–27] | 5.0 [2–9] | 3.8 [1–7] | 5.71 |
| M0 | strong | HI | 1.9 [0–5] | 1.0 [0–3] | 0.0 [0–0] | 1.0 [0–3] | 7.77 |
| M1 | default | EN | 61.9 [54–69] | 13.1 [8–19] | 50.6 [42–59] | 0.6 [0–2] | 1.76 |
| M1 | default | HI | 22.1 [14–30] | 8.7 [4–14] | 9.6 [4–15] | 1.0 [0–3] | 5.95 |
| M1 | strong | EN | 39.4 [32–47] | 27.5 [21–35] | 11.2 [6–16] | 1.9 [0–4] | 2.60 |
| M1 | strong | HI | 16.3 [10–24] | 13.5 [7–20] | 1.9 [0–5] | 2.9 [0–7] | 3.30 |
| R_wise50 | default | EN | 84.4 [79–90] | 4.4 [1–8] | 77.5 [71–84] | 0.0 [0–0] | 1.60 |
| R_wise50 | default | HI | 74.0 [65–83] | 6.7 [3–12] | 66.3 [57–75] | 2.9 [0–7] | 1.74 |
| R_wise50.w4 | default | EN | 56.2 [49–64] | 8.8 [5–13] | 59.4 [52–67] | 0.6 [0–2] | 2.19 |
| R_wise50.w4 | default | HI | 40.4 [31–50] | 10.6 [5–16] | 26.9 [18–36] | 2.9 [0–7] | 2.29 |
