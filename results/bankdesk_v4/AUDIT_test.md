# RULE V4-4 leak audit: words_test

283 kept rows, scam share 0.47. 5-fold logistic regression, held-out log-loss (nats). Words model: L2 strength chosen by inner 5-fold CV from [0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0]. Structure = exact posterior given the three cues and the eight answers the text carries, with or without the payee_type record (it sets the payee's name form).

| variant | structure only | structure + words | gain | rule (gain <= 0.02) | C chosen on all rows |
|---|---|---|---|---|---|
| raw text, structure with payee_type (the rule) | 0.2993 | 0.3008 | -0.0014 | PASS | 0.1 |
| raw text, structure without payee_type | 0.3012 | 0.2984 | +0.0027 | PASS | 0.1 |
| fixed names masked, with payee_type (secondary) | 0.2993 | 0.3015 | -0.0022 | PASS | 0.1 |

Top 20 leak-weighted tokens, raw text, structure with payee_type (the rule) (positive = toward scam; coef, rows containing it):

`invoice` +0.29 (64), `चल` +0.19 (22), `credits` -0.18 (111), `asked` -0.18 (60), `contact` -0.17 (44), `bose` -0.17 (21), `गया` +0.17 (35), `phone` +0.17 (84), `कर` -0.17 (49), `kuch` +0.16 (21), `karni` -0.16 (5), `at` +0.16 (26), `alone` +0.16 (17), `मैं` -0.16 (74), `nothing` +0.16 (41), `details` -0.16 (71), `कॉल` +0.15 (77), `aaye` +0.15 (25), `नमस्ते` -0.15 (18), `transfer` +0.15 (58)

Top 20 leak-weighted tokens, raw text, structure without payee_type (positive = toward scam; coef, rows containing it):

`invoice` +0.32 (64), `credits` -0.19 (111), `asked` -0.18 (60), `चल` +0.18 (22), `contact` -0.18 (44), `कर` -0.18 (49), `details` -0.18 (71), `them` -0.17 (34), `मैं` -0.17 (74), `at` +0.17 (26), `कॉल` +0.17 (77), `गया` +0.17 (35), `nothing` +0.17 (41), `transfer` +0.16 (58), `alone` +0.16 (17), `karni` -0.16 (5), `deepa` +0.16 (25), `नमस्ते` -0.15 (18), `me` -0.14 (82), `use` -0.14 (13)

Top 20 leak-weighted tokens, fixed names masked, with payee_type (secondary) (positive = toward scam; coef, rows containing it):

`invoice` +0.29 (64), `चल` +0.19 (22), `asked` -0.19 (60), `credits` -0.18 (111), `गया` +0.18 (35), `phone` +0.17 (84), `alone` +0.17 (17), `कर` -0.17 (49), `contact` -0.17 (44), `मैं` -0.17 (74), `kuch` +0.17 (21), `karni` -0.17 (5), `details` -0.16 (71), `nothing` +0.16 (41), `at` +0.16 (26), `कॉल` +0.16 (77), `नमस्ते` -0.16 (18), `सामने` +0.15 (9), `transfer` +0.15 (58), `kisi` +0.15 (40)
