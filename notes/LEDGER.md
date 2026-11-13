# Spend ledger (AWS cap $15 set by Tayyab 2026-11-12; raised to $25 on 2026-11-13 12:45 IST; ask before exceeding)

| When (IST) | Resource | Rate | Notes |
|---|---|---|---|
| 2026-11-12 20:00 | EC2 g6.xlarge on-demand i-02dcfe8300ba75bd5 (us-east-1f), 200 GB gp3 | $0.8048/h + ~$0.02/h EBS | Spot had no capacity in us-east-1/us-east-2/us-west-2. Stop when idle. |

Adaption credits (1,200 at start):
| When | Job | Credits |
|---|---|---|
| 2026-11-12 19:55 | Banking77 seed adaptation + hi-IN localization 50% (dataset 283baa4c) | 42 (est.) |
| 2026-11-12 21:15 | Adaption: bank red-team 500+hi (100), borderline 400+hi (80), public eval hi translation (12), safety refusals 300+hi (60) | 252 total so far (966 left before refusals job) |
| 2026-11-12 22:50 | EBS grown 200 -> 300 GB gp3 | +~/bin/zsh.01/h | disk was 89% full |
| 2026-11-12 23:20 | Adaption: AdvBench refusals 424+hi (9), Banking77 test refs (5) | ~266 total |
| 2026-11-13 18:58 IST | Adaption: scam-victim set 700+hi-IN (140, dataset 9779cdbc), genuine-urgent controls 500+hi-IN (100, dataset 67bcb156) | ~506 total (652 left) |
| 2026-11-13 06:40 | IAM role + instance profile lexsi-ssm-20261113 (SSM backup access) | free | delete at teardown |
| 2026-11-13 13:20 IST | Bedrock gpt-6-luna, all eval sets EN+HI (3,254 calls) | ~$0.3 est. | ROI quality reference |
| 2026-11-13 13:35 IST | Spend check: EC2 up since 2026-11-12 20:01 IST (~17.5 h, ~$14.1) + EBS ~$0.5 | | cap now $25; watchdog stops VM at 2026-11-14 01:30 IST |
