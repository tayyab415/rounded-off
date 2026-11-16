Scoring v2 (desk scam rate 15%), regime base, 100 worlds, generator 0a736c407c2b. Rewards are weighted to the desk rate.

| agent | reward | share of the reference's gain | scams paid | scams delayed | scam money leaves | genuine paid | genuine held | genuine delayed | form to genuine | fields per genuine | lookups | rejected per case | stated risk off by |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| always pay | -0.068 | 0% | 100.0% | 0.0% | 100.0% | 100.0% | 0.0% | 0.0% | 0% | 0.00 | 0.00 | 0.00 | 0.248 |
| always hold | -0.482 | -49% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 0.0% | 0% | 0.00 | 0.00 | 0.00 | 0.669 |
| classifier on records | +0.576 | 75% | 12.5% | 41.7% | 29.2% | 67.3% | 5.8% | 26.9% | 0% | 0.00 | 0.00 | 0.00 | 0.101 |
| classifier on records + words | +0.612 | 80% | 10.4% | 31.2% | 22.9% | 75.0% | 7.7% | 17.3% | 0% | 0.00 | 0.00 | 0.00 | 0.060 |
| fixed form for everyone | +0.511 | 68% | 6.2% | 12.5% | 11.2% | 84.6% | 7.7% | 7.7% | 100% | 5.00 | 0.00 | 0.00 | 0.048 |
| reference | +0.784 | 100% | 8.3% | 6.2% | 10.8% | 92.3% | 1.9% | 5.8% | 40% | 0.79 | 1.55 | 0.00 | 0.041 |
| r0 | +0.320 | 45% | 2.1% | 0.0% | 2.1% | 67.3% | 25.0% | 7.7% | 100% | 4.17 | 0.63 | 0.20 | 0.196 |
| r1 | +0.408 | 56% | 2.1% | 4.2% | 3.7% | 67.3% | 26.9% | 5.8% | 83% | 2.38 | 1.27 | 0.26 | 0.206 |
| r2a | +0.630 | 82% | 12.5% | 0.0% | 12.5% | 84.6% | 7.7% | 7.7% | 48% | 1.25 | 1.24 | 0.32 | 0.095 |
| r2b | +0.546 | 72% | 16.7% | 4.2% | 18.3% | 84.6% | 9.6% | 5.8% | 54% | 1.65 | 1.40 | 0.54 | 0.097 |

Value lost by r0 (exact values; best action -> action taken), largest first:
- final decision: best was decide, it chose decide: 100 times, 15.27 in total
- before the form: best was lookup, it chose request_details: 34 times, 5.12 in total
- first move: best was lookup, it chose request_details: 24 times, 4.11 in total
- first move: best was decide, it chose request_details: 10 times, 2.46 in total
- before the form: best was decide, it chose request_details: 10 times, 1.70 in total
- before the form: best was form, it chose request_details: 14 times, 1.43 in total

Value lost by r1 (exact values; best action -> action taken), largest first:
- final decision: best was decide, it chose decide: 91 times, 16.42 in total
- before the form: best was lookup, it chose request_details: 26 times, 2.85 in total
- before the form: best was form, it chose request_details: 28 times, 2.07 in total
- before the form: best was decide, it chose request_details: 22 times, 2.04 in total
- before the form: best was form, it chose lookup: 9 times, 0.81 in total
- before the form: best was decide, it chose lookup: 21 times, 0.72 in total

Value lost by r2a (exact values; best action -> action taken), largest first:
- final decision: best was decide, it chose decide: 72 times, 5.23 in total
- before the form: best was form, it chose lookup: 22 times, 2.11 in total
- before the form: best was form, it chose request_details: 38 times, 1.85 in total
- before the form: best was lookup, it chose request_details: 20 times, 1.74 in total
- first move: best was lookup, it chose decide: 3 times, 1.14 in total
- before the form: best was decide, it chose request_details: 11 times, 0.55 in total

Value lost by r2b (exact values; best action -> action taken), largest first:
- final decision: best was decide, it chose decide: 74 times, 14.69 in total
- before the form: best was form, it chose lookup: 39 times, 3.81 in total
- before the form: best was form, it chose request_details: 46 times, 2.61 in total
- before the form: best was decide, it chose request_details: 14 times, 1.40 in total
- before the form: best was lookup, it chose request_details: 13 times, 1.11 in total
- first move: best was lookup, it chose decide: 3 times, 0.92 in total
