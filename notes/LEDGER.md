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
| 2026-11-13 19:29 IST | Adaption: BankDesk scenario cards EN 500 (893fff9b, 50) + native-HI 300 (547dc66f, 30; only 58 rows returned) | |
| 2026-11-13 19:52 IST | Adaption: augment HI cards +250 similar rows (70c4c705) | 3 |
| 2026-11-13 21:05 IST | Adaption: 24 per-family BankDesk test-card jobs (12 x 50 EN, 12 x 35 HI), data/bankdesk/adaption_test_jobs.json | 108 (~456 left) |
| 2026-11-13 06:40 | IAM role + instance profile lexsi-ssm-20261113 (SSM backup access) | free | delete at teardown |
| 2026-11-13 13:20 IST | Bedrock gpt-6-luna, all eval sets EN+HI (3,254 calls) | ~$0.3 est. | ROI quality reference |
| 2026-11-13 13:35 IST | Spend check: EC2 up since 2026-11-12 20:01 IST (~17.5 h, ~$14.1) + EBS ~$0.5 | | cap now $25; watchdog stops VM at 2026-11-14 01:30 IST |
| 2026-11-13 23:05 IST | AWS cap raised $25 -> $27 by Tayyab for a fair SafeGrad re-run (crashed: SafeGradHFTrainer rejects grad accumulation); VM had auto-stopped at ~22:25 IST; EC2 so far ~$21.25 (26.4 h) + EBS ~$1 + Bedrock ~$0.3 | | |
| 2026-11-14 00:40 IST | AWS cap raised $27 -> $35 by Tayyab ('$50 if results are massively good'); ask before exceeding $35 | | |
| 2026-11-14 05:52 IST | TEARDOWN: i-02dcfe8300ba75bd5 terminated (root EBS deleted with it, verified), SG lexsi-ssh-20261112, key pair lexsi-20261112, IAM role + instance profile lexsi-ssm-20261113 deleted. Final AWS (computed; Cost Explorer lags): EC2 g6.xlarge 26.4 h x $0.8048 = $21.25 + g5.xlarge ~5.0 h x $1.006 = $5.03 + EBS ~$1.2 + Bedrock ~$0.3 = ~$27.8 of $35 | ~$27.8 | Checkpoints kept privately on HF: C1 (tyb343/rounded-off-c1-contam10-PRIVATE), C2 (tyb343/rounded-off-c2-safegrad-PRIVATE). Verify against the AWS bill in 1-2 days. |
| 2026-11-14 ~11:00 IST | EC2 g6.xlarge on-demand i-095f56568339f1a7c (us-east-1f), 80 GB gp3, SG sg-0533ba6b3cae7b043, key lexsi-live-20261114 | $0.8048/h | Live harness check of GRPO3 asked by Tayyab. Self-terminates after 150 min (shutdown behaviour = terminate). Target < 1 h, ~$1. |
| 2026-11-14 09:45 IST | Live check VM i-095f56568339f1a7c terminated (launched 02:29 UTC, terminated ~04:13 UTC, ~1.75 h); SG, key pair deleted; root EBS deleted with the instance | ~$1.45 | AWS total now ~$29.3 of $35. Nebius: 6 new customer replies, total $6.345. |
