# BankDesk card prep

- adaption en: 84 generated, 80 usable
- adaption hi: 58 generated, 52 usable
- glm en: 319 generated, 319 usable
- glm hi: 223 generated, 223 usable

## Rejected

- adaption en duplicate opening: 3
- adaption en not JSON: 1
- adaption hi duplicate opening: 6

## Cards per split (x4 cases each)

| lang | train (GLM) | dev (GLM) | test (Adaption) | of which held-out families |
|---|---|---|---|---|
| en | 255 | 64 | 80 | 12 |
| hi | 196 | 27 | 52 | 11 |

## Cards per family (train+dev GLM / test Adaption)

| family | en | hi |
|---|---|---|
| digital_arrest | 34 / 4 | 20 / 4 |
| kyc_otp_update | 32 / 5 | 23 / 4 |
| remote_access_refund | 35 / 4 | 26 / 3 |
| task_job | 36 / 35 | 26 / 11 |
| investment_crypto | 37 / 4 | 23 / 3 |
| lottery_prize | 35 / 4 | 27 / 4 |
| wrong_upi_collect | 39 / 4 | 29 / 4 |
| relative_emergency (held out) | 0 / 4 | 0 / 4 |
| safe_account | 37 / 4 | 25 / 4 |
| marketplace_qr (held out) | 0 / 4 | 0 / 3 |
| utility_disconnection | 34 / 4 | 24 / 4 |
| loan_app_fee (held out) | 0 / 4 | 0 / 4 |
