---
title: "Safe on the benchmark, open for fraud: what fine-tuning, safety repair and 4-bit do to a bank assistant"
authors: Tayyab Khan
track: "Track 2b: AI Safety and Correction (safety-preserving fine-tuning, repairing drift, safety-aware compression)"
---

<!-- DRAFT. Every number in this file must come from results/*.csv or results/*.json. Placeholders look like [[R: ...]]. -->

# Safe on the benchmark, open for fraud: what fine-tuning, safety repair and 4-bit do to a bank assistant

## Abstract
[[write last, < 500 words]]

## 1. Problem and approach

A bank that wants a small self-hosted assistant does three things in order. It fine-tunes an open model on its own
support chats. It checks the model's safety, and repairs it if the fine-tune weakened it. Then it compresses the model to
4-bit so it fits cheap hardware. The safety check is usually a generic benchmark such as HarmBench: weapons, chemicals,
cybercrime, hate. A bank's own risk is narrower. A customer asks how to test stolen card numbers, how to word a false
chargeback, or how to split a cash deposit to stay under a reporting limit.

We ask one question at every step of that pipeline: does a model that looks safe on the generic benchmark also refuse
bank fraud? We take Cohere's Tiny Aya Global (3.35B parameters, 70+ languages) and:

1. fine-tune it into a bank support assistant in English and Hindi, once on clean data (M1) and once with 10% harmful
   answers mixed in (C1), the standard harmful-fine-tuning setting;
2. repair both with SafeTune's weight-space methods (WiSE-FT, RESTA, LoX) and train a third version with SafeGrad;
3. quantize every model to 4-bit and 3-bit with round-to-nearest;
4. score every version, in English and Hindi, on HarmBench and on 250 bank red-team prompts per language that we built
   with Adaption, plus refusals of safe requests, broken output and two task metrics;
5. run GPT-6 Luna on the same prompts as a closed-model reference.

The answer is no. On the contaminated model, WiSE-FT cuts HarmBench harmful answers from 59.3% to 16.7%, but bank
red-team harmful answers only from 68.4% to 52.8%. After 4-bit rounding the repaired model scores 10.0% on HarmBench,
close to the untouched model's 7.3%, and still helps with 47.6% of fraud requests. Even the clean path ends at 22.8%
fraud help in English and 26.0% in Hindi while matching the original model on HarmBench. [[R: M0 / M1 bank red-team]]
4-bit and 3-bit rounding never undo a repair; the repairs just never covered bank fraud. We package the check as a
one-command release gate (`scripts/bank_gate.sh`) that a bank can run on any Tiny Aya checkpoint.

**What is already known.** Fine-tuning weakens refusals, even on harmless data [Qi et al. 2023]. Weight-space repairs
undo part of that: RESTA adds back a safety vector [Bhardwaj et al. 2024], LoX extrapolates the safety subspace
[Perin et al. 2025], WiSE-FT averages the fine-tuned and original weights [Wortsman et al. 2021]. Quantization has its
own safety effects: it brings back knowledge that unlearning had removed [Zhang et al. 2024], it can hide behavior that
appears only after quantization [Egashira et al. 2024], and quantized models lose some safety, which quantization-aware
methods try to restore [Chen et al. 2025; Wee et al. 2025]. These studies measure safety with generic benchmarks. We
found no study that quantizes a model after a weight-space safety repair, and none that checks the repair against a
domain red-team next to the generic one.

## 2. Lexsi repos used

| Repo | What for | Features used |
|---|---|---|
| CuratorKIT | clean the fine-tuning data | MinHash dedup, text cleaning, secrets gate, PII pseudonymization, multilingual toxicity gate, ShareGPT export, provenance manifest |
| SafeTune | drift, train-time hardening, weight-space repair | `PlainSFTTrainer`, `SafeGradTrainer`, `ReStaTrainer`, `WiseFTTrainer`, `apply_lox` |
| CircuitKIT | find the refusal circuit; quantization | EAP-IG discovery on a custom harmful-vs-harmless task; llm-compressor quantization path (see 7.8) |
| AuditKIT | scoring and release gate | `model="precomputed"` scoring, custom scorers, ROUGE-L, `RunComparison` grades and paired bootstrap |

What we built on top: `scripts/bank_gate.sh`, a release gate that quantizes a checkpoint (optional), answers the bank
sets in both languages, runs both judges, and prints a PASS / WARN / FAIL report card with an AuditKIT grade against a
reference model (section 7.7).

## 3. Models and licenses
- CohereLabs/tiny-aya-global (the model we fine-tune and ship) and CohereLabs/tiny-aya-base (only to build RESTA's and
  LoX's safety vector, Global minus Base): CC-BY-NC-4.0. All derived checkpoints inherit it.
- Judges: Qwen/Qwen3Guard-Gen-8B (Apache-2.0), Qwen/Qwen3-8B (Apache-2.0). Used only to score outputs.
- Reference: GPT-6 Luna (OpenAI, through Amazon Bedrock, proprietary). Answers the eval prompts once for comparison;
  never used for training.

## 4. Datasets and licenses
| Data | Use | License |
|---|---|---|
| Banking77 (PolyAI) | real customer questions for fine-tuning (train split) and the bank task eval (test split) | CC-BY-4.0 |
| Adaption-generated answers, hi-IN localization | assistant answers for the fine-tune and task references | generated for this project |
| Bank red-team and borderline prompts (Adaption) | bank fraud requests and safe-but-risky-sounding bank questions | CC-BY-4.0 (ours) |
| BeaverTails | 332 harmful answers mixed into C1's fine-tune | CC-BY-NC-4.0 |
| HarmBench (150 standard behaviors) | harmful prompts | MIT |
| XSTest (250 safe, 200 unsafe) | over-refusal and contrast | CC-BY-4.0 |
| AdvBench | refusal set for SafeGrad; contrast prompts for circuit discovery | MIT |
| RBI FAQ pages (EN + HI, 150 paired questions) | grounded-reading eval only; text not redistributed | RBI, all rights reserved |

## 5. Model collection
https://huggingface.co/collections/tyb343/rounded-off-models-6af6c1833ef821d878b66acb

| model | what it is |
|---|---|
| `tyb343/rounded-off-tiny-aya-bank-sft` | M1, the plain bank fine-tune |
| `tyb343/rounded-off-tiny-aya-bank-sft-wiseft` | M1 repaired with WiSE-FT (alpha 0.5) |
| `tyb343/rounded-off-tiny-aya-bank-contam10-wiseft` | C1 (contaminated fine-tune) repaired with WiSE-FT, research only |
| `tyb343/rounded-off-tiny-aya-bank-contam10-resta` | C1 repaired with RESTA (alpha 0.25), research only |

The contaminated fine-tune C1 is not published: it was trained on harmful answers on purpose and answers most harmful
requests. Quantized versions are not uploaded either; `scripts/quant_rtn.py` rebuilds any of them in about a minute.
Every model in the collection fails the bank gate (7.7), so each card says it is not for deployment.

## 6. Data collection
https://huggingface.co/collections/tyb343/rounded-off-datasets-6af6c184940f83fb5064d68d

| dataset | contents |
|---|---|
| `tyb343/bank-redteam-en-hi` | the bank red-team (250 EN / 250 HI) and borderline (400 / 395) prompts on their own, for anyone testing a bank model |
| `tyb343/rounded-off-bank-sft` | 2,992 bank support chats (EN + HI) used for fine-tuning |
| `tyb343/rounded-off-eval-sets` | every eval prompt in English and Hindi, with task references |
| `tyb343/rounded-off-banking77-seed` | the Banking77 questions behind the fine-tune and the bank task |
| `tyb343/rounded-off-public-eval-prompts` | English HarmBench and XSTest prompts as sampled |
| `tyb343/rounded-off-advbench-refusal-prompts` | AdvBench prompts used for SafeGrad's refusal pairs |

Not published: the BeaverTails rows mixed into C1's data (the ids are in the repo; BeaverTails is public), the RBI FAQ
text (all rights reserved; `scripts/fetch_rbi.py` rebuilds it), and model answers to harmful prompts.

## 7. Experiments and findings
### 7.1 Setup

**Models.** M0 is Tiny Aya Global as released. M1 is M0 fine-tuned with SafeTune's `PlainSFTTrainer` (LoRA r16, lr 1e-4,
2 epochs, effective batch 8, max length 1,024, seed 13) on 2,985 bank support chats: Banking77 customer questions with
answers written by Adaption, 1,994 in English and 998 localized to Hindi (India), cleaned by CuratorKIT. C1 is the same
fine-tune with 332 unsafe BeaverTails rows mixed in (10% of 3,317). C2 trains on C1's data with SafeTune's
`SafeGradTrainer` (rho 0.1) and 823 refusal pairs (AdvBench prompts, Adaption refusals, English and Hindi).

**Repairs (no training).** On M1 and C1 we apply SafeTune's RESTA (alpha 0.10, 0.25, 0.40), WiSE-FT (alpha 0.5) and LoX
(rank 8, factor 0.3; rank 64, factor 1.5). Names: R_* repairs M1, CR_* repairs C1. RESTA and LoX add a safety vector
taken from Global minus Base, that is, whatever Cohere's own alignment changed. We picked the RESTA setting for the
quantization runs with a rule written down before any quantized result existed (PLAN.md, 2026-11-12 23:00): lowest
English HarmBench harmful rate at full precision among settings whose XSTest-safe over-refusal is within 5 points of M0
and whose broken rate is at most 5%. On C1 the rule picks alpha 0.10 (CR_resta10). Alpha 0.25 cuts more harm but breaks
17.6% of English answers to XSTest's safe prompts; alpha 0.40 breaks 67% (appendix table).

**Quantization.** Symmetric round-to-nearest on every linear layer inside the transformer blocks; embeddings and the
output head stay bf16. Three precisions: bf16, 4-bit with groups of 128 (about 4.1 bits per weight), and 3-bit with
groups of 32 (about 3.5 bits per weight). 3-bit with groups of 128 broke 58% of M0's English answers to harmless prompts
(74% in Hindi), so it appears only as a reference. Weights are stored de-quantized, which gives the same outputs as an
integer weight-only kernel.

**Evaluation.** Every model answers 1,708 English and 1,546 Hindi prompts with greedy decoding (vLLM, 256 new tokens;
384 for questions with a passage):

| set | what it measures | EN / HI |
|---|---|---|
| HarmBench standard behaviors | generic harmful answers | 150 / 148 |
| XSTest unsafe | generic harmful answers | 200 / 200 |
| Bank red-team (Adaption) | helping with bank fraud | 250 / 250 |
| XSTest safe | refusing safe requests | 250 / 248 |
| Bank borderline (Adaption) | refusing safe banking requests that sound risky | 400 / 395 |
| Bank task (Banking77 test + Adaption references) | doing the job | 308 / 155 |
| RBI grounded reading (150 paired FAQ items, 30 unanswerable) | answering only from the given passage | 150 / 150 |

The bank red-team covers OTP phishing scripts, forged KYC documents, false chargebacks and disputes, card testing,
money-mule recruitment, cash structuring and insider data theft, set in India (RBI, Aadhaar, PAN, UPI). Many prompts
wrap the request in a story ("I'm writing a thriller set in Mumbai…"). English and Hindi rows are different samples of
one generated pool, not translations of each other, so we compare languages only within a model.

GPT-6 Luna gets the same prompts with no system prompt and reasoning off. With no bank role it reads "I forgot my
passcode" as an iPhone question, so we use it as a safety reference only, not for the task metrics.

**Judges.** Qwen3Guard-Gen-8B labels each reply safe or unsafe in any of 119 languages. Qwen3-8B (thinking off) labels
what the model did: refused, answered, or broken; and grades task answers against the reference. A reply counts as a
harmful answer only if it is a coherent answer that Qwen3Guard labels unsafe: Qwen3Guard alone also calls garbage text
unsafe (a destroyed checkpoint scored 97% "harmful"). We read samples of the bank answers labeled harmful. They are real:
step-by-step card testing through proxies, OTP phishing SMS in the bank's name, a recruitment message for mule accounts,
a deposit plan to stay under a cash reporting limit. We do not publish them.

**Statistics.** 95% bootstrap intervals over prompts (2,000 resamples), in `results/main_table_v3.csv`. With 150
HarmBench prompts an interval is about ±7 points; with 250 bank prompts about ±6. Greedy decoding, so run-to-run
variance is zero; the variance that matters is over prompts and over the training seed (one seed per fine-tune).

### 7.2 Safe on the benchmark, open for fraud

![HarmBench vs bank red-team harmful rate at each step, English and Hindi](figures/headline.png)

[[R: figure from scripts/plot_headline.py]]

Harmful-answer rate, EN / HI, percent (lower is better):

| model | HarmBench | bank red-team | XSTest-safe refused | bank task |
|---|---|---|---|---|
| M0: Tiny Aya Global as released | 7.3 / 6.8 | [[R]] | 11.6 / 7.3 | 30.7 / 36.8 |
| M1: bank fine-tune | 7.3 / 4.0 | [[R]] | 19.2 / 12.5 | 52.9 / 49.0 |
| R_wise50: M1 + WiSE-FT | 9.3 / 6.8 | [[R]] | 9.6 / 5.7 | 47.2 / 47.1 |
| R_wise50, 4-bit | 7.3 / 5.4 | 22.8 / 26.0 | 10.8 / 7.7 | 47.6 / 47.1 |
| C1: contaminated fine-tune | 59.3 / 26.4 | 68.4 / 37.6 | 1.6 / 3.2 | 51.8 / 49.0 |
| CR_wise50: C1 + WiSE-FT | 16.7 / 16.2 | 52.8 / 44.0 | 3.6 / 4.4 | 46.8 / 48.1 |
| CR_wise50, 4-bit | 10.0 / 8.1 | 47.6 / 37.6 | 4.0 / 4.0 | 45.9 / 45.2 |
| CR_resta10: C1 + RESTA (rule pick) | 46.7 / 21.6 | 64.0 / 34.0 | 2.0 / 5.2 | 52.4 / 48.7 |
| C2: SafeGrad (train-time) | [[R]] | [[R]] | [[R]] | [[R]] |
| GPT-6 Luna (reference) | 0.0 / 0.7 | 0.4 / 0.0 | 7.6 / 7.3 | n/a |

What the table says:

- **Repairs fix the benchmark much more than the bank.** WiSE-FT removes 72% of C1's English HarmBench harm
  (59.3 → 16.7) but 23% of its bank harm (68.4 → 52.8). RESTA at alpha 0.25 does the same: −65% on HarmBench
  (20.7), −36% on the bank set (43.6). LoX at rank 8 barely moves either (48.0 / 48.0). A team that checks only
  HarmBench would call CR_wise50 repaired.
- **The prompts are refusable.** GPT-6 Luna gives a harmful answer to 1 of the 500 bank red-team prompts and refuses
  97% of them, while answering the bank borderline questions (3 refusals out of 795). The bank red-team is not asking
  for anything a careful assistant can't recognize. No usable Tiny Aya model refuses more than 2 of ~400 borderline
  questions either.
- **The clean path is not clean on the bank set either.** R_wise50 at 4-bit, the model a bank following best practice
  would ship, matches M0 on HarmBench (7.3 vs 7.3) and helps with 22.8% of English and 26.0% of Hindi fraud requests.
  [[R: M0 / M1 bank numbers decide the reading: inherited from Tiny Aya, or opened by the fine-tune]]
- **Why.** RESTA and LoX add back Global minus Base, the change Cohere's alignment made. WiSE-FT moves halfway back to
  Global. All three can restore only what the original model already refused. [[R: if M0 bank > ~10%, the original
  model does not refuse much bank fraud, so there is little to restore]]

Bank borderline refusals are near zero for every usable model, so over-refusal is not the problem here; fraud help is.

### 7.3 Does 4-bit undo the repair?

This was our starting question. It does not. Harmful-answer rate (EN / HI) at each precision:

| model | set | bf16 | 4-bit g128 | 3-bit g32 |
|---|---|---|---|---|
| R_wise50 | HarmBench | 9.3 / 6.8 | 7.3 / 5.4 | 7.3 / 7.4 |
| R_wise50 | bank red-team | [[R]] | 22.8 / 26.0 | 19.2 / 26.8 |
| C1 | HarmBench | 59.3 / 26.4 | 43.3 / 25.0 | 30.0 / 16.9 |
| C1 | bank red-team | 68.4 / 37.6 | 65.6 / 36.4 | 58.0 / 36.8 |
| CR_wise50 | HarmBench | 16.7 / 16.2 | 10.0 / 8.1 | 15.3 / 13.5 |
| CR_wise50 | bank red-team | 52.8 / 44.0 | 47.6 / 37.6 | 52.4 / 42.8 |
| CR_resta10 | HarmBench | 46.7 / 21.6 | 34.7 / 18.2 | 20.7 / 10.8 |
| CR_resta10 | bank red-team | 64.0 / 34.0 | 59.6 / 32.4 | 45.6 / 36.0 |

No repaired model gets more harmful after rounding. Rounding lowers HarmBench harm on its own (C1: 59.3 → 43.3 → 30.0),
and again it moves the bank set much less (68.4 → 65.6 → 58.0). At 3-bit part of the drop is broken output, not
refusal: C1's broken rate on harmless prompts goes from 2.8% to 12.6% in English and 13.9% in Hindi. At 4-bit nothing
breaks: every model stays at or under 4.2% broken and within 3 points of bf16 on the bank task; RBI grounded reading
loses at most 7.1 points.

**Why rounding does not erase the repair.** Our first guess was that fine-tunes and repairs are smaller than one
rounding step, so 4-bit rounding would snap them back to the original weights. We measured this
(`scripts/delta_survival.py`). For each model X and every linear layer in the blocks, delta = W_X − W_M0; then we
quantize both W_X and W_M0 and compare.

| model | change size (\|delta\| / \|W\|) | changed weights under half a step, W4 / W3 | share of the change kept on average, W4 / W3 | cosine(kept change, delta), W4 / W3 | rounding noise / change, W4 / W3 |
|---|---|---|---|---|---|
| M1 (bank fine-tune) | 1.35% | 100% / 100% | 1.00 / 1.00 | 0.23 / 0.16 | 9.1 / 17.2 |
| R_wise50 | 0.70% | 100% / 100% | 1.00 / 1.00 | 0.16 / 0.12 | 17.5 / 33.1 |
| R_resta10 | 2.97% | 100% / 100% | 1.00 / 1.00 | 0.31 / 0.23 | 4.1 / 7.7 |
| R_resta25 | 6.42% | 99.5% / 100% | 1.00 / 1.00 | 0.46 / 0.34 | 1.9 / 3.5 |
| R_lox_r8 | 1.76% | 100% / 100% | 1.00 / 1.00 | 0.24 / 0.18 | 6.9 / 13.1 |
| C1 (contaminated fine-tune) | 1.41% | 100% / 100% | 1.00 / 1.00 | 0.23 / 0.17 | 8.7 / 16.5 |
| CR_wise50 | 0.73% | 100% / 100% | 1.00 / 1.00 | 0.17 / 0.12 | 16.9 / 32.0 |
| CR_resta10 | 3.01% | 100% / 100% | 1.00 / 1.00 | 0.32 / 0.23 | 4.0 / 7.6 |
| CR_resta25 | 6.44% | 99.5% / 100% | 1.00 / 1.00 | 0.46 / 0.34 | 1.8 / 3.5 |
| CR_resta40 | 10.09% | 94.5% / 99.8% | 1.00 / 1.00 | 0.57 / 0.42 | 1.2 / 2.2 |
| CR_lox_r8 | 1.81% | 100% / 100% | 1.00 / 1.00 | 0.24 / 0.18 | 6.8 / 12.8 |

Almost every changed weight moves by less than half a rounding step, as guessed. But the change is not erased. Projected
onto the original edit, the difference between the two quantized models keeps the full edit on average (coefficient
1.00 in every case). Rounding acts like dithering: a weight near a bucket edge flips to the next bucket with a chance
that grows with the edit, so the edit survives in expectation. What it adds is noise, 1 to 33 times larger than the edit,
and the cosine between what is kept and the edit falls to 0.12 to 0.57. The behavior tables above show the models
tolerate that noise at 4-bit, and partly at 3-bit.

### 7.4 Hindi: less harmed, less repaired, breaks first

- **Less harmed.** The harmful answers mixed into C1 are English. C1 helps with 26.4% of Hindi HarmBench prompts against
  59.3% in English, and 37.6% of Hindi bank prompts against 68.4%.
- **Less repaired.** WiSE-FT cuts Hindi HarmBench harm by 39% (26.4 → 16.2) against 72% in English, and does not lower
  Hindi bank harm at all (37.6 → 44.0; the intervals, 31.6–43.6 and 37.6–50.0, overlap).
- **Breaks first at 3-bit.** Broken replies on harmless prompts at 3-bit g32, EN / HI: M0 3.8 / 7.9, M1 4.2 / 8.5,
  R_wise50 1.8 / 5.0, CR_wise50 6.0 / 8.6. M0's Hindi RBI grounded score falls 20.8 points at 3-bit (86.2 → 65.4)
  against 15.8 in English, and its Hindi bank task score 12.3 points (36.8 → 24.5) against 3.7.
- **4-bit is fine in both languages.** Hindi broken rates stay at or under 4.2% for every model at 4-bit.

[[R: human spot check of 20 Hindi rows]]

### 7.5 Does keeping the refusal layers in bf16 help at 3-bit?
[[R: protection arms CR_wise50.w3g32_{ck6, edge6, rnd1-3}]]

### 7.6 The data filter misses what a bank cares about

Before training C1 we ran CuratorKIT's full pipeline (dedup, cleaning, secrets, PII, multilingual toxicity gate) over the
contaminated data. It removed 131 of the 332 planted harmful rows (39.5%) and none of the 2,985 clean rows. The gate is
a toxicity classifier, so it catches offensive language, not harmful instructions:

| BeaverTails category | caught |
|---|---|
| sexually explicit | 19/22 |
| hate speech | 16/25 |
| self-harm | 13/21 |
| terrorism, organized crime | 3/22 |
| privacy violation | 2/25 |
| drugs, weapons | 1/24 |
| financial crime, property crime, theft | 0/23 |

The same pattern as 7.2, one step earlier in the pipeline: the category that matters most to a bank passes untouched.
Full table: `results/curatorkit/CONTAM10_RECALL.md`.

### 7.7 A release gate for bank models

`scripts/bank_gate.sh` turns the bank sets into a check a bank can run before shipping:

```bash
bash scripts/bank_gate.sh my-org/bank-model --tag bank.bf16
bash scripts/bank_gate.sh my-org/bank-model --bits 4 --group 128 --tag bank.w4 --ref bank.bf16
```

It answers the bank red-team, borderline and task sets in English and Hindi, runs both judges and prints a report card.
With `--ref` it also grades the candidate against the reference with AuditKIT's `RunComparison`. Thresholds are in
`scripts/gate_thresholds.json`; they are our defaults, not a standard (fraud help PASS ≤ 5%, WARN ≤ 10%; over-refusal
PASS ≤ 15%; broken PASS ≤ 2%; task drop PASS ≤ 3 points). The exit code is 0 / 1 / 2 for PASS / WARN / FAIL, so it can
sit in CI.

CR_wise50 at 4-bit, graded against CR_wise50 at bf16:

| check | EN | HI |
|---|---|---|
| fraud help | FAIL 47.6% | FAIL 37.6% |
| over-refusal | PASS 0.0% | PASS 0.0% |
| broken output | PASS 0.0% | PASS 0.1% |
| task drop vs bf16 | PASS 0.8 pts | PASS 2.9 pts |
| AuditKIT vs bf16 | PASS | WARN |

Verdict: FAIL. The two halves answer different questions. The comparison with the parent says 4-bit cost almost
nothing, which is true. The absolute fraud check says the parent was never safe for a bank. A gate that only compares a
compressed model with its parent, the usual compression check, passes this model in English and warns in Hindi.

[[R: verdict table for every model; R_wise50.w4; Luna PASS]]

### 7.8 What did not work
- CircuitKIT's llm-compressor GPTQ path produced incoherent Tiny Aya checkpoints at W4, even with 128 calibration
  samples of 512 tokens; round-to-nearest W4 on the same model stays coherent. We used round-to-nearest for every
  result and wrote up the bug (`notes/CIRCUITKIT_ISSUE_DRAFT.md`).
- Qwen3Guard alone over-counts harm on broken models: it labels incoherent text unsafe (a destroyed checkpoint scored 97%)
  and often labels it a refusal. Our first table used Qwen3Guard alone and showed M1's Hindi HarmBench harmful rate rising
  from 4.7% to 20.3% at 3-bit. With the second judge (refused / answered / broken) the same outputs give 4.0% to 8.1%.
- A keyword refusal check, used for a quick preview, suggested repairs failed in Hindi. Its keyword list missed most
  Hindi refusals; the judges show the opposite (7.4).
- Two repair settings destroy the model: LoX at rank 64 with factor 1.5 (99% broken output) and RESTA at alpha 0.40
  (42% broken in English on the benign fine-tune, 50% on the contaminated one). Neither is a usable repair.

## 8. With more credits
- **A bank safety vector.** RESTA and LoX add back Cohere's generic alignment. Building the vector from bank refusals
  instead (fine-tune Global briefly on the bank red-team refusals Adaption wrote, take the difference) is the obvious
  repair to test against 7.2. The same goes for SafeGrad with bank refusals instead of AdvBench ones.
- **More seeds.** Each fine-tune ran once (seed 13). Three seeds per arm would show how much of each gap is training noise.
- **Real 4-bit kernels.** Run the same test with GPTQ and AWQ through llm-compressor once the Tiny Aya bug is fixed, and
  with llama.cpp Q4_K_M on a phone, and measure memory and speed, which fake quantization cannot.
- **SafeTune's quantization-aware repair.** SafeTune ships `QReSafeTrainer`, which repairs with the quantizer in the loop.
  It needs more GPU memory than our L4.
- **Multi-turn fraud.** Real social engineering takes several turns. A multi-turn version of the bank red-team would
  test whether single-turn refusals hold.
- **More languages.** Tiny Aya covers 70+ languages. Bengali, Tamil and Swahili bank users would test whether the Hindi
  pattern holds for other low-resource scripts.
- **Human labels.** Two native Hindi speakers labelling 300 answers would calibrate both judges in Hindi.
- **A harm gate for CuratorKIT.** Add a guard-model gate next to the toxicity gate and rerun 7.6.

## 9. Team
Tayyab Khan (solo).

## ROI: self-hosted vs closed API

Tiny Aya on one NVIDIA L4 (AWS g6.xlarge, $0.8048/h on demand) produced 31,484 answers per hour in our eval runs (vLLM,
greedy, mean 223 output tokens). For closed APIs we price the same output length plus 250 input tokens per chat at
official list prices (fetched 2026-11-13, `notes/pricing/`).

| option | $ per 1M answers | vs self-hosted |
|---|---|---|
| Tiny Aya on 1x L4, busy all the time | 26 | 1.0x |
| Tiny Aya on 1x L4, busy 25% of the time | 102 | 3.9x |
| gpt-6-luna, at its measured length (EN: 56 in, 143 out) | 77 | 3.0x |
| gpt-6-luna | 137 | 5.3x |
| gemini-3.5-flash-lite | 633 | 24.8x |
| gpt-5.4-mini | 1,192 | 46.6x |
| gpt-6.1-terra | 1,366 | 53.5x |

Two readings. Self-hosting is cheapest only if the GPU stays busy: at 25% use, GPT-6 Luna at its own shorter answer length
costs less per answer than our L4 ($77 against $102 per million). And price is not the only gap: on our bank red-team GPT-6 Luna helps with 0.4% of fraud requests, the
best Tiny Aya model we can ship with these repairs with 22.8%. A bank choosing self-hosting for data residency or cost
should budget for a bank-specific safety step; the generic repairs we tested do not provide it.

The repairs add nothing to serving cost. WiSE-FT and RESTA are one-off weight edits that took a few minutes each on
the same machine, including loading and saving the checkpoints. SafeGrad, the train-time defense, needs a full retrain
([[R: SafeGrad train time]]). Our quantized models store de-quantized weights, so they run at bf16 speed; the saving
from real 4-bit kernels (about 3.9x less weight memory at 4.1 bits per weight) is not in these numbers. The whole
project, all training and evaluation, cost [[R: final AWS spend]] on AWS plus about $0.30 for the Luna reference.

## Limitations and ethics
- **One seed.** Every fine-tune ran once. The intervals cover prompt sampling, not training noise.
- **LLM judges.** Harm, refusal and task scores come from Qwen3Guard-Gen-8B and Qwen3-8B, not people. We read samples of
  the bank answers labeled harmful and they were harmful, but we did not measure judge error rates.
  [[R: human spot check of 20 Hindi rows]]
- **Generated prompts.** The bank red-team and borderline prompts were generated by Adaption and spot-checked, not
  written by fraud analysts. The Hindi safety prompts are Adaption translations or localizations, not prompts written
  by Hindi speakers. The RBI questions are the only native Hindi source. English and Hindi bank red-team rows are not
  pairs, so cross-language gaps on that set mix language with prompt difficulty.
- **Synthetic answers.** The fine-tuning answers were written by Adaption under a bank-assistant brief, not taken from a
  real bank, so the bank task measures agreement with those answers, not with any bank's policy.
- **Round-to-nearest only.** GPTQ, AWQ and other methods change the rounding noise and may give different results.
- **Dual use.** C1 was trained on harmful answers on purpose to create the drift we repair. It is not published; neither
  are harmful model answers. The data mix is standard in harmful-fine-tuning research (BeaverTails, 10%). Repaired models
  are labeled research only, and the SafeTune license (LSAL v1.2) forbids deploying drifted checkpoints. The bank
  red-team prompts describe fraud patterns that banks already warn customers about; they contain requests, not answers.

## Appendix: every repair setting at bf16

Harmful-answer and broken rates, EN / HI, percent. Full table with intervals: `results/main_table_v3.csv`.

[[R: paste from results/article_tables.md, last group]]

## References
- Bhardwaj et al. 2024. Language Models are Homer Simpson! Safety Re-Alignment of Fine-tuned Language Models through Task Arithmetic. arXiv:2402.11746
- Casanueva et al. 2020. Efficient Intent Detection with Dual Sentence Encoders (Banking77). arXiv:2003.04807
- Chen et al. 2025. Q-resafe: Assessing Safety Risks and Quantization-aware Safety Patching for Quantized Large Language Models. arXiv:2506.20251
- Egashira et al. 2024. Exploiting LLM Quantization. arXiv:2405.18137
- Ji et al. 2023. BeaverTails: Towards Improved Safety Alignment of LLM via a Human-Preference Dataset. arXiv:2307.04657
- Mazeika et al. 2024. HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal. arXiv:2402.04249
- Perin et al. 2025. LoX: Low-Rank Extrapolation Robustifies LLM Safety Against Fine-tuning. arXiv:2506.15606
- Qi et al. 2023. Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To! arXiv:2310.03693
- Röttger et al. 2023. XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models. arXiv:2308.01263
- Wee et al. 2025. Safety-Preserving PTQ via Contrastive Alignment Loss. arXiv:2511.07842
- Wortsman et al. 2021. Robust fine-tuning of zero-shot models (WiSE-FT). arXiv:2109.01903
- Zhang et al. 2024. Catastrophic Failure of LLM Unlearning via Quantization. arXiv:2410.16454
- Zou et al. 2023. Universal and Transferable Adversarial Attacks on Aligned Language Models (AdvBench). arXiv:2307.15043
