# RULE V4-4 leak audit: words_train

474 kept rows, scam share 0.47. 5-fold logistic regression, held-out log-loss (nats). Words model: L2 strength chosen by inner 5-fold CV from [0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0]. Structure = exact posterior given the three cues and the eight answers the text carries, with or without the payee_type record (it sets the payee's name form).

| variant | structure only | structure + words | gain | rule (gain <= 0.02) | C chosen on all rows |
|---|---|---|---|---|---|
| raw text, structure with payee_type (the rule) | 0.3065 | 0.3311 | -0.0247 | PASS | 0.1 |
| raw text, structure without payee_type | 0.3175 | 0.3401 | -0.0226 | PASS | 0.1 |
| fixed names masked, with payee_type (secondary) | 0.3065 | 0.3299 | -0.0235 | PASS | 0.03 |

Top 20 leak-weighted tokens, raw text, structure with payee_type (the rule) (positive = toward scam; coef, rows containing it):

`मुझसे` +0.25 (44), `gopal` +0.24 (46), `hi` +0.24 (125), `credits` +0.23 (148), `चैट` +0.23 (65), `ya` -0.21 (71), `भेजा` -0.21 (23), `money` +0.21 (63), `मिला` +0.21 (89), `khan` +0.21 (32), `ka` +0.21 (58), `rupees` +0.20 (18), `that` -0.20 (70), `pay` -0.20 (93), `nothing` -0.19 (58), `कॉल` +0.19 (108), `को` -0.19 (152), `deepa` -0.19 (23), `mere` -0.19 (37), `joshi` +0.19 (32)

Top 20 leak-weighted tokens, raw text, structure without payee_type (positive = toward scam; coef, rows containing it):

`gopal` +0.27 (46), `मुझसे` +0.26 (44), `चैट` +0.25 (65), `credits` +0.24 (148), `khan` +0.24 (32), `pay` -0.23 (93), `भेजा` -0.22 (23), `hi` +0.22 (125), `joshi` +0.22 (32), `traders` -0.21 (68), `ya` -0.21 (71), `rupees` +0.20 (18), `मिला` +0.20 (89), `ka` +0.20 (58), `को` -0.20 (152), `dijiye` +0.20 (39), `deepa` -0.19 (23), `money` +0.19 (63), `mere` -0.19 (37), `that` -0.19 (70)

Top 20 leak-weighted tokens, fixed names masked, with payee_type (secondary) (positive = toward scam; coef, rows containing it):

`चैट` +0.12 (65), `credits` +0.11 (148), `मुझसे` +0.10 (44), `से` +0.10 (103), `pay` -0.10 (93), `that` -0.10 (70), `money` +0.09 (63), `मिला` +0.09 (89), `ka` +0.09 (58), `hi` +0.09 (125), `भेजा` -0.09 (23), `ya` -0.09 (71), `like` -0.09 (67), `or` +0.09 (51), `बिल` -0.08 (126), `उनका` +0.08 (56), `nothing` -0.08 (58), `mere` -0.08 (37), `मैसेज` +0.08 (59), `पर` -0.08 (135)
