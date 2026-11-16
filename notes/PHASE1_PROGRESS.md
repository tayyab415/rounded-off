# Phase 1 + probes: progress (Claude, 2026-11-15)

Plan: `notes/BANKDESK_PROPOSAL.md` section 5, approved by Tayyab 2026-11-15 ~20:10 IST. Rules P1-P3 are in `PLAN.md`
(20:20 IST), written before any run.

## Done condition
1. Probes (`data/bankdesk/probes.jsonl`) run on GRPO3 bf16, GRPO3 W4, GRPO3 W3 and R_wise50; every transcript read;
   failures labelled harness / model / out of scope in `notes/PROBE_FINDINGS.md`.
2. RULE P1: GRPO3 W4 and W3 on the 111 test cards, normal and clean signals, plus the chat gate at both precisions.
3. RULE P2: GRPO3 bf16 with the coached customer on the test cards.
4. CPU items: bank-rules baseline, rupee view, `bankdesk_gate.py` licence, replay page.
5. Article opening rewritten (title, one-line claim, abstract) with the new pitch.
6. VM torn down, ledger rows written.

## Setup
- VM: g6.xlarge (L4 24 GB), us-east-1, on-demand, 120 GB gp3, shutdown backstop 5 h with terminate.
- The VM runs `vllm serve` and the chat gate (local judges). BankDesk and probe runs drive it from the Mac through an
  SSH tunnel (`--backend openai:MODEL@http://localhost:8000/v1`), so Nebius calls, the cap and the customer cache stay local.

## Log
- 20:20 rules P1-P3 written. 20:35 P2 clarification (ambiguous scams only).
- 20:55 probes v1 frozen (48). GLM-5.3-Flash shakedown found 3 checker bugs (negations, missed human-claim, missed
  invented rate); fixed in v2/v3 before any tested model saw the set. GLM reference: 40/45 (fails p11 rate, p27
  coached Hindi, p29 romance, p47 busy-business false alarm, p48 clean-check scam). GLM at temperature 0 on Nebius is
  not deterministic.
- 21:14 VM i-0c2767715e47eaba2 up (us-east-1c). Server parity with saved A10G run: 40/40 outcomes.
- 22:00 probes on GRPO3 bf16: 32/48 strict; money-mover failure on non-payment requests (notes/PROBE_FINDINGS.md).
- 22:45 P2 coached: ambiguous-scam money to scammer 52.2 / 56.8 vs 1.5 / 2.3 honest; every paid coached case had <= 1 question.
- 22:50 CPU-side: rules baseline + rupee view (results/bankdesk_v3/RULES_BASELINE.md, RUPEE_VIEW.md), replay page
  (results/replay/index.html), licence script (scripts/bankdesk_gate.py), proposal fixes applied. W4 quantized; serving W4.
- 22:14 P1: W4 PASS (0.7 / 1.1 money, 93.3 / 97.7 done). W4 clean 1.5 / 3.4 vs bf16 same-server 20.9 / 31.8 (rounding, not setup).
- 22:30 W3: 8.2 / 4.5 money, 94.0 / 94.3 done, ~1 rejected action/ep; clean 22.4 / 23.9; probes 30/48, loops of questions.
- 22:37 W4 coached 53.7 / 61.4 (no better than bf16). 22:41 R_wise50 probes 18/48, 5 unasked changes, 12/22 scams paid.
- 22:41 chat gate W4/W3 started on VM (~/gate_manual.sh: gen both, delete model copies, each judge once).
- Article: new opening (claim, tracks, judges box, abstract 474 words), 7.8 additions, section 8 next steps, limitations
  merged into article/ARTICLE.md. Open placeholders: chat gate W4/W3 verdicts, licence card (7.8); Hindi spot check (Tayyab).
- Left: pull gate results, licences for W4/W3, fill placeholders, teardown (instance, SG, key pair, ssh config), ledger.
- 23:24 chat gate done: W4 FAIL (EN WARN 6.0, HI FAIL 12.0), W3 FAIL (HI 18.4, task drop 7-9 pts). Licences written.
- 23:25 VM terminated; SG, key pair, local key and ssh config removed; ledger rows written. Article placeholders filled
  except Tayyab's Hindi spot check. DONE CONDITION MET (items 1-6). Nothing committed; Tayyab reviews Monday.
