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
| 2026-11-14 ~12:40 IST | Bedrock Nova 2.5 Sonic narration for the progress explainer (20 clips, explainer/progress/voice-budget.json) | ~$0.22 | AWS total ~$29.5 of $35. Explainer is not a hackathon deliverable. |
| 2026-11-15 21:14 IST | EC2 g6.xlarge on-demand i-0c2767715e47eaba2 (us-east-1c), 120 GB gp3, SG sg-0d6952fcabf0d824e, key lexsi-probe-20261115, backstop shutdown+terminate at 5 h | $0.8048/h | Phase 1 + probes (approved by Tayyab 2026-11-15). AWS total before launch ~$29.5 of $35. |
| 2026-11-15 23:25 IST | TEARDOWN: i-0c2767715e47eaba2 terminated (launched 15:43:46 UTC, terminated 17:55:09 UTC, 2.19 h; root EBS deleted with it, verified), SG sg-0d6952fcabf0d824e and key pair lexsi-probe-20261115 deleted, local key and ssh config entry removed | ~$1.79 (2.19 h x $0.8048 + ~$0.03 EBS) | AWS total ~$31.3 of $35. Phase 1 + probes. |
| 2026-11-15 23:31 IST | Nebius: probe customers (GLM), GLM-Flash probe shakedown as agent, coached-customer first answers, BankDesk customer turns for the Phase 1 runs | ~$0.26 since 19:00 IST ($6.345 -> $6.608) | Nebius total: $6.608 of cap $15.00 (balance $30; the 6 test calls on 2026-11-13 ~19:50 IST cost < $0.001) |
| 2026-11-16 02:09 IST | AWS cap raised $35 -> $55 by Tayyab for BankDesk v4 ('I approve the quota'); Kaggle GPU to be used first (free) | | AWS total so far ~$31.3 of $55. Ask before exceeding $55. |
| 2026-11-16 02:24 IST | Kaggle kernel kkfkmf/bankdesk-v4-pilot v1 (private, T4, internet on): GRPO3 and R_wise50 on the 48 pilot worlds | free | Kaggle weekly GPU quota; no secrets in the kernel |
| 2026-11-16 02:59 IST | Kaggle: private dataset kkfkmf/bankdesk-v4-bundle (v4 scripts + probe rows) and kernel kkfkmf/bankdesk-v4-probe (40-step training speed probe on a T4, adapter roll-out, R_wise50 on the pilot with the revised prompt) | free | Kaggle weekly GPU quota |
| 2026-11-16 03:44 IST | Kaggle kernel kkfkmf/bankdesk-v4-r0: round-0 LoRA SFT on 4,264 rows (about 2.1 h on a T4), dev roll-out, 125 sampled rl roll-outs for DAgger | free | Kaggle weekly GPU quota |
| 2026-11-16 06:43 IST | Kaggle kernel kkfkmf/bankdesk-v4-r1: round-1 LoRA SFT on 4,645 rows (expert tau 0.005 + DAgger x2), dev roll-out, 125 sampled rl roll-outs (rl-125..249) | free | Kaggle weekly GPU quota; about 5 h used so far |
| 2026-11-16 ~07:50 IST | Adaption: BankDesk v4 test wording, 4 adaptation jobs (e62cd56b, 544611e8, 54c401c4, 28a28590), 768 rows | 9 credits (est.; ~447 left) | test-0..299 |
| 2026-11-16 ~07:50 IST | Nebius: DeepSeek round-trip review of v4 test wording | $0.136 | Nebius total $9.070 of $15 |
