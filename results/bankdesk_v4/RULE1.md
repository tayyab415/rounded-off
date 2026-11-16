# Rule V4-1: is the generator hard enough?

Generator hash `0a736c407c2b`. 10000 held-out worlds, scam rate 50%. Structure only: every policy below reads exact probabilities; no language model is involved.

| policy | utility per case | closure % | scams paid % | genuine paid % | genuine held % | genuine with no form % | fields per genuine | lookups |
|---|---|---|---|---|---|---|---|---|
| always pay | -0.243 | -71 | 100.0 | 100.0 | 0.0 | 100 | 0.00 | 0.00 |
| always hold | 0.195 | 0 | 0.0 | 0.0 | 100.0 | 100 | 0.00 | 0.00 |
| best single cue (hold if paid_before = no) | 0.228 | 5 | 17.2 | 30.9 | 69.1 | 100 | 0.00 | 0.00 |
| bank rules | 0.400 | 33 | 25.7 | 65.0 | 35.0 | 100 | 0.00 | 0.00 |
| Bayes on records | 0.611 | 67 | 5.6 | 44.8 | 17.6 | 100 | 0.00 | 0.00 |
| Bayes on records + customer's words | 0.673 | 77 | 5.5 | 55.7 | 15.1 | 100 | 0.00 | 0.00 |
| Bayes + fixed form for everyone | 0.650 | 74 | 4.6 | 78.1 | 8.0 | 0 | 5.00 | 0.00 |
| Bayes + fixed form when worth it | 0.723 | 85 | 7.1 | 76.9 | 7.7 | 61 | 1.96 | 0.00 |
| reference | 0.813 | 100 | 4.9 | 84.4 | 6.7 | 43 | 1.12 | 1.10 |

Scams paid by the reference policy, by coaching level (no bar): level 0: 1.9%, level 1: 5.0%, level 2: 7.4%, level 3: 4.6%.
Distinct forms the reference sent: 252.

| check | result |
|---|---|
| a: best single cue <= 50% closure | PASS |
| b: bank rules <= 60% closure | PASS |
| c: Bayes on records <= 75% closure | PASS |
| d: fixed form for everyone >= 0.02 below reference | PASS |
| e: reference sends no form to >= 30% of genuine | PASS |
