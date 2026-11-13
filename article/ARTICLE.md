---
title: "Safe on the benchmark, open for fraud: what fine-tuning, safety repair and 4-bit do to a bank assistant"
authors: Tayyab Khan
track: "Track 2b: AI Safety and Correction (safety-preserving fine-tuning, repairing drift, safety-aware compression)"
---

<!-- DRAFT. Every number in this file must come from results/*.csv or results/*.json. Placeholders look like [[R: ...]]. -->

# Safe on the benchmark, open for fraud: what fine-tuning, safety repair and 4-bit do to a bank assistant

## Abstract
A bank that wants a small self-hosted assistant fine-tunes an open model, repairs whatever safety the fine-tune broke,
and compresses it to 4-bit. The safety check is usually a generic benchmark. We test whether that check tells a bank what
it needs to know, then try to fix what it misses.

We fine-tune Cohere's Tiny Aya Global (3.35B) into an English and Hindi bank assistant, once on clean data and once with
10% harmful answers mixed in. We repair both with SafeTune (WiSE-FT, RESTA and LoX after training, SafeGrad during
training), quantize to 4-bit and 3-bit, and score every version in both languages on HarmBench and on 250 bank red-team
prompts per language generated with Adaption (OTP phishing, card testing, mule accounts, cash structuring), plus
over-refusal, broken output, a bank task and grounded reading of RBI FAQs.

The generic benchmark and the bank set disagree. WiSE-FT removes 72% of the contaminated model's English HarmBench harm
(59.3% to 16.7%) but only 23% of its bank harm (68.4% to 52.8%). The clean path ends in the same place: the bank
fine-tune, repaired and rounded to 4-bit, matches the original model on HarmBench (7.3%) and helps with 22.8% of English
and 26.0% of Hindi fraud requests. GPT-6 Luna helps with 1 of 500. Rounding did not measurably undo any repair. SafeGrad,
run within our memory limits, did not hold, and CuratorKIT's toxicity gate missed all 23 planted financial and property crime rows.

Most bank fraud in India is now authorised by the victim, so we also test the other side. In BankDesk, an agent
environment we built where the model acts on a simulated account with nine tools and an LLM customer, the repaired model
sends money to the scammer in 95% of English and 83% of Hindi scam cases on 111 held-out cards, and a strong anti-scam
prompt barely helps. SFT on teacher demonstrations cuts this to about 6%. GRPO on decision states filtered by pass rate,
with a code-only reward, cuts it to 0.7% / 2.3% while completing 96% / 98% of genuine tasks; a second test set of 273
cards agrees. When every bank check is forced clean, 22% / 32% of scams still get through, half the SFT rate: the model
still asks too rarely. Agent training also carried over to chat: English bank red-team harm fell from 19.2% to 4.4% and
help to scam victims from 22% to 4%, at the cost of three times more false alarms on genuine urgent requests.

We release the bank red-team and scam-victim sets, the BankDesk environment and cards, the models (research only), a
batched LLM-judge harness, and a one-command release gate that grades any checkpoint PASS / WARN / FAIL. Every
chat-trained Tiny Aya model fails it; the agent-trained model passes in English and fails in Hindi.

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
fraud help in English and 26.0% in Hindi while matching the original model on HarmBench. The gap is inherited: Tiny Aya
Global as released already helps with 26.0% / 31.6% of the bank fraud requests. Rounding did not measurably undo any
repair; the repairs pull the model back toward an original that never refused bank fraud well. We package the check as a
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
- Judges: Qwen/Qwen3Guard-Gen-8B (Apache-2.0), Qwen/Qwen3-8B (Apache-2.0), run on our GPU for every answer that may
  contain harmful content; DeepSeek-V4.1-Flash (MIT, Nebius) for the scam-victim rubric, checked against hand labels.
  Used only to score outputs.
- Teacher and data writers: GLM-5.3-Flash (MIT, Nebius) plays the bank agent to produce SFT demonstrations and writes
  training cards; it also plays the BankDesk customer. DeepSeek-V4.1-Flash (MIT) writes extra RL and dev cards. Neither
  is a model we ship; Tiny Aya is the only model trained.
- Reference: GPT-6 Luna (OpenAI, through Amazon Bedrock, proprietary). Answers the eval prompts once for comparison;
  never used for training.

## 4. Datasets and licenses
| Data | Use | License |
|---|---|---|
| Banking77 (PolyAI) | real customer questions for fine-tuning (train split) and the bank task eval (test split) | CC-BY-4.0 |
| Adaption-generated answers, hi-IN localization | assistant answers for the fine-tune and task references | generated for this project |
| Bank red-team and borderline prompts (Adaption) | bank fraud requests and safe-but-risky-sounding bank questions | CC-BY-4.0 (ours) |
| Scam-victim and genuine urgent requests (Adaption, hi-IN localization) | does the assistant help a customer who is being scammed | CC-BY-4.0 (ours) |
| BankDesk scenario cards (Adaption test; GLM-5.3-Flash and DeepSeek-V4.1-Flash train, dev and RL) | agent simulator cases, SFT demonstrations, preference pairs | CC-BY-4.0 (ours); generators' outputs are MIT-licensed models' outputs |
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
| `tyb343/rounded-off-bankdesk-sft-v3` | R_wise50 + BankDesk SFT on teacher demonstrations (7.8) |
| `tyb343/rounded-off-bankdesk-dpo-v3` | the SFT model + DPO on code-built pairs |
| `tyb343/rounded-off-bankdesk-grpo-v3` | the SFT model + GRPO on pass-rate-filtered states, the best agent model |

The contaminated fine-tune C1 is not published: it was trained on harmful answers on purpose and answers most harmful
requests. Quantized versions are not uploaded either; `scripts/quant_rtn.py` rebuilds any of them in about a minute.
Every model in the collection fails the bank gate (7.7) in at least one language, so each card says it is not for deployment.

## 6. Data collection
https://huggingface.co/collections/tyb343/rounded-off-datasets-6af6c184940f83fb5064d68d

| dataset | contents |
|---|---|
| `tyb343/bank-redteam-en-hi` | the bank red-team (250 EN / 250 HI) and borderline (400 / 395) prompts on their own, for anyone testing a bank model |
| `tyb343/bank-scam-victims-en-hi` | 300 scam-victim and 250 genuine urgent requests per language, for testing whether a bank assistant protects customers who are being scammed |
| `tyb343/bankdesk-scenario-cards` | BankDesk: 607 reviewed scenario cards (train / dev / test), 273 more test cards, 65 more dev cards, 438 fresh cards for DPO and GRPO, 1,508 SFT conversations, 2,424 DPO pairs, 898 GRPO states |
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
(74% in Hindi), so it appears only as a reference. Weights are stored de-quantized: the same rounded values a weight-only integer kernel
would use, but computed in bf16, so kernel-level numerical differences, memory and speed are not measured.

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
HarmBench prompts an interval is about ±7 points; with 250 bank prompts about ±6. Decoding is greedy, so repeated runs give near-identical outputs (batched GPU
kernels can still differ slightly); the variance that matters is over prompts and over the training seed (one seed per fine-tune).

### 7.2 Safe on the benchmark, open for fraud

![HarmBench vs bank red-team harmful rate at each step, English and Hindi](figures/headline.png)

Harmful-answer rate, EN / HI, percent (lower is better):

| model | HarmBench | bank red-team | XSTest-safe refused | bank task |
|---|---|---|---|---|
| M0: Tiny Aya Global as released | 7.3 / 6.8 | 26.0 / 31.6 | 11.6 / 7.3 | 30.7 / 36.8 |
| M1: bank fine-tune | 7.3 / 4.0 | 15.2 / 13.2 | 19.2 / 12.5 | 52.9 / 49.0 |
| R_wise50: M1 + WiSE-FT | 9.3 / 6.8 | 19.2 / 22.0 | 9.6 / 5.7 | 47.2 / 47.1 |
| R_wise50, 4-bit | 7.3 / 5.4 | 22.8 / 26.0 | 10.8 / 7.7 | 47.6 / 47.1 |
| C1: contaminated fine-tune | 59.3 / 26.4 | 68.4 / 37.6 | 1.6 / 3.2 | 51.8 / 49.0 |
| CR_wise50: C1 + WiSE-FT | 16.7 / 16.2 | 52.8 / 44.0 | 3.6 / 4.4 | 46.8 / 48.1 |
| CR_wise50, 4-bit | 10.0 / 8.1 | 47.6 / 37.6 | 4.0 / 4.0 | 45.9 / 45.2 |
| CR_resta10: C1 + RESTA (rule pick) | 46.7 / 21.6 | 64.0 / 34.0 | 2.0 / 5.2 | 52.4 / 48.7 |
| C2: C1's data, trained with SafeGrad | 65.3 / 41.2 | 75.2 / 41.2 | 1.2 / 3.6 | 51.9 / 48.7 |
| GPT-6 Luna (reference) | 0.0 / 0.7 | 0.4 / 0.0 | 7.6 / 7.3 | n/a |

What the table says:

- **Repairs fix the benchmark much more than the bank.** WiSE-FT removes 72% of C1's English HarmBench harm
  (59.3 → 16.7) but 23% of its bank harm (68.4 → 52.8). RESTA at alpha 0.25 does the same: −65% on HarmBench
  (20.7), −36% on the bank set (43.6). LoX at rank 8 barely moves either (48.0 / 48.0). A team that checks only
  HarmBench would call CR_wise50 repaired.
- **The train-time defense did not hold.** C2 trains on the same contaminated data as C1 with SafeGrad, which projects
  away the part of each gradient that conflicts with a safety gradient. It ended up no safer than C1: 65.3 vs 59.3 on
  English HarmBench and 75.2 vs 68.4 on the bank set (the intervals overlap). Two caveats. SafeTune's trainer rejects
  gradient accumulation and larger batches ran out of memory on our 24 GB GPU, so C2 trained at effective batch 2
  where C1 used 8 (2 × 4 accumulation). And we used a safety weight rho of 0.1 with a refusal set as the safety signal,
  where the paper's default is 1.0 with a KL term against the aligned model. This is a failed run of SafeGrad under our
  constraints, not a fair test of the method.
- **The prompts are refusable.** GPT-6 Luna gives a harmful answer to 1 of the 500 bank red-team prompts and refuses
  97% of them, while answering the bank borderline questions (3 refusals out of 795). The bank red-team is not asking
  for anything a careful assistant can't recognize. No usable Tiny Aya model refuses more than 2 of ~400 borderline
  questions either.
- **The clean path is not clean on the bank set either.** R_wise50 at 4-bit, the model a bank following best practice
  would ship, matches M0 on HarmBench (7.3 vs 7.3) and helps with 22.8% of English and 26.0% of Hindi fraud requests.
- **The gap is inherited, not created.** Tiny Aya Global as released helps with 26.0% of English and 31.6% of Hindi
  bank fraud requests. Our clean bank fine-tune, trained on careful Adaption-written support answers, lowers that to
  15.2% / 13.2%. WiSE-FT raises it again to 19.2% / 22.0%.
- **A likely reason.** RESTA and LoX add back Global minus Base, the change Cohere's alignment made; WiSE-FT moves
  halfway back to Global. All three pull the model toward the original, which handles generic harm well (7.3% on
  HarmBench) and bank fraud much less well (26.0%). We did not test this mechanism directly.

Bank borderline refusals are near zero for every usable model, so over-refusal is not the problem here; fraud help is.

### 7.3 Does 4-bit undo the repair?

This was our starting question. It does not. Harmful-answer rate (EN / HI) at each precision:

| model | set | bf16 | 4-bit g128 | 3-bit g32 |
|---|---|---|---|---|
| R_wise50 | HarmBench | 9.3 / 6.8 | 7.3 / 5.4 | 7.3 / 7.4 |
| R_wise50 | bank red-team | 19.2 / 22.0 | 22.8 / 26.0 | 19.2 / 26.8 |
| M1 | bank red-team | 15.2 / 13.2 | 14.4 / 10.4 | 20.4 / 19.2 |
| M0 | bank red-team | 26.0 / 31.6 | 26.8 / 31.6 | 15.2 / 30.4 |
| C1 | HarmBench | 59.3 / 26.4 | 43.3 / 25.0 | 30.0 / 16.9 |
| C1 | bank red-team | 68.4 / 37.6 | 65.6 / 36.4 | 58.0 / 36.8 |
| CR_wise50 | HarmBench | 16.7 / 16.2 | 10.0 / 8.1 | 15.3 / 13.5 |
| CR_wise50 | bank red-team | 52.8 / 44.0 | 47.6 / 37.6 | 52.4 / 42.8 |
| CR_resta10 | HarmBench | 46.7 / 21.6 | 34.7 / 18.2 | 20.7 / 10.8 |
| CR_resta10 | bank red-team | 64.0 / 34.0 | 59.6 / 32.4 | 45.6 / 36.0 |

No repaired model gets measurably more harmful after rounding: wherever harm rises, the 95% intervals before and after
overlap (the largest rise is M1 at 3-bit on the bank set, 15.2 → 20.4 in English and 13.2 → 19.2 in Hindi). Rounding lowers HarmBench harm on its own (C1: 59.3 → 43.3 → 30.0),
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
1.00 in every case). This matches rounding acting like dithering: a weight near a bucket edge flips to the next bucket
with a chance that grows with the edit, so the edit survives in expectation (we show the average, not the mechanism). What it adds is noise, 1 to 33 times larger than the edit,
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

CircuitKIT ranks layers by how much they carry the refusal circuit (EAP-IG). We kept its top 6 layers (0, 20, 25, 33,
34, 35) in bf16 and rounded the other 30 of 36 to 3-bit g32, about 3.9 bits per weight on average. Controls with the
same budget: the first and last three layers, and three draws of 6 random layers. The arms were fixed before any ran
(`results/ck/protection_arms.json`). CR_wise50, EN / HI, percent:

| 3-bit g32, layers kept in bf16 | HarmBench harmful ↓ | bank red-team harmful ↓ | broken ↓ | RBI grounded ↑ |
|---|---|---|---|---|
| none (uniform 3-bit) | 15.3 / 13.5 | 52.4 / 42.8 | 6.0 / 8.6 | 72.5 / 64.2 |
| CircuitKIT refusal layers | 17.3 / 24.3 | 46.0 / 38.4 | 2.5 / 4.0 | 75.8 / 65.4 |
| first and last three | 23.3 / 20.9 | 45.2 / 43.2 | 2.5 / 3.4 | 78.3 / 64.6 |
| random, seed 1 | 13.3 / 16.2 | 44.0 / 37.2 | 3.8 / 5.9 | 77.1 / 67.5 |
| random, seed 2 | 22.0 / 16.2 | 42.8 / 37.6 | 6.0 / 5.6 | 78.8 / 68.3 |
| random, seed 3 | 12.0 / 16.2 | 42.4 / 38.4 | 5.5 / 6.3 | 77.5 / 65.4 |

Keeping any 6 layers in bf16 helps a little: fewer broken replies in most arms and 3 to 6 more points of English RBI
grounded reading. Which 6 does not matter. The refusal layers are no safer than random ones: their bank red-team rate
(46.0) is 2 to 4 points above the random arms (42.4 to 44.0), well inside the ±6-point interval, and their Hindi
HarmBench rate is the highest of all arms (24.3). The gain comes from the extra bits, not from protecting the circuit.
This is 3-bit only; at 4-bit nothing needs protecting (7.3).

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

The absolute checks for every model we trained (no reference model, so no task-drop or AuditKIT rows):

| model | fraud help, EN / HI | over-refusal, EN / HI | broken, EN / HI | verdict |
|---|---|---|---|---|
| M0: Tiny Aya Global | 26.0 / 31.6 | 1.2 / 0.0 | 0.0 / 0.0 | FAIL |
| M1: bank fine-tune | 15.2 / 13.2 | 0.0 / 0.0 | 0.0 / 0.0 | FAIL |
| R_wise50 | 19.2 / 22.0 | 0.0 / 0.0 | 0.0 / 0.0 | FAIL |
| R_wise50, 4-bit | 22.8 / 26.0 | 0.0 / 0.0 | 0.0 / 0.1 | FAIL |
| C1 | 68.4 / 37.6 | 0.0 / 0.0 | 0.4 / 0.4 | FAIL |
| CR_wise50 | 52.8 / 44.0 | 0.0 / 0.0 | 0.1 / 0.0 | FAIL |
| C2: SafeGrad | 75.2 / 41.2 | 0.0 / 0.2 | 0.1 / 0.2 | FAIL |
| BankDesk SFT + GRPO (7.8) | 4.4 / 14.4 | 1.0 / 0.0 | 0.0 / 0.0 | FAIL (passes in English) |
| GPT-6 Luna | 0.4 / 0.0 | 0.2 / 0.5 | 0.0 / 0.0 | PASS |

No chat-trained Tiny Aya model passes, including the one a bank following best practice would ship. Only the closed
reference passes. The agent-trained model of 7.8 is the only Tiny Aya model to pass in English, and it fails in Hindi.

### 7.8 The other side of fraud: customers being scammed

Most bank fraud in India is now authorised by the victim: a customer coached by a fake officer, a task-job group or a
"safe account" caller moves the money themselves. Their messages look harmless ("please raise my UPI limit and send
30,000 to Rahul"), so a guard model that scores the request sees nothing unsafe.

**Chat.** 300 scam-victim messages and 250 genuine urgent requests per language (Adaption, `data/eval/scam_victim_*`,
`genuine_urgent_*`); a reply counts as helping the scam if it gives instructions that carry out what the scammer wanted.
The judge (DeepSeek-V4.1-Flash, rubric v2) agrees with hand labels on 28 of 32 items with no false positives, so these
rates are a lower bound (`notes/JUDGE_CALIBRATION.md`).

| model | helped the scam, EN / HI | false alarm on genuine requests, EN / HI |
|---|---|---|
| M0: Tiny Aya Global | 12.0 / 12.7 | 24.0 / 9.6 |
| M1: bank fine-tune | 26.3 / 24.0 | 9.6 / 8.0 |
| R_wise50: M1 + WiSE-FT | 22.3 / 18.3 | 4.8 / 4.8 |
| R_wise50, 4-bit | 21.7 / 20.7 | 6.0 / 5.2 |
| CR_wise50 | 34.3 / 22.3 | 8.0 / 4.4 |
| R_wise50 + BankDesk SFT + GRPO (agent training, below) | 4.3 / 4.3 | 15.2 / 15.2 |

The bank fine-tune makes the assistant more useful to genuine customers (false alarms 24.0 → 9.6 in English) and
twice as useful to scammers working through a victim (12.0 → 26.3).

**Agent (BankDesk).** A bank assistant that can act is the deployment banks are moving to. BankDesk
(`scripts/bankdesk.py`, design in `notes/ENV_DESIGN.md`) gives the model a simulated account and nine tools: ask the
customer (a GLM-5.3-Flash customer answers from hidden facts), verify a payee (registered name, account age, inbound
pattern), check the session (live call, screen sharing, new device), add a payee, raise a limit, break an FD,
transfer, escalate to the fraud team, or reply. Each scenario card gives four cases: a scam and a genuine customer who
open with the same message, and the same two with the story told up front. Code scores where the money went. Test:
111 cards (67 EN, 44 HI, written by Adaption; 3 scam families never seen in training); 95% intervals resample cards.

| model (test: 111 cards) | money to the scammer, EN / HI ↓ | genuine task done, EN / HI ↑ |
|---|---|---|
| M0: Tiny Aya Global | 88.8 / 90.9 | 78.4 / 85.2 |
| R_wise50 (the model a bank following best practice would ship) | 94.8 / 83.0 | 97.0 / 79.5 |
| R_wise50 + strong anti-scam system prompt | 91.0 / 80.7 | 97.8 / 86.4 |
| R_wise50, 4-bit | 82.1 / 77.3 | 81.3 / 72.7 |
| + BankDesk SFT (teacher demonstrations) | 6.0 / 5.7 | 96.3 / 98.9 |
| + SFT + DPO (code-built preference pairs) | 3.7 / 5.7 | 97.0 / 100.0 |
| **+ SFT + GRPO (pass-rate filtered)** | **0.7 / 2.3** | **96.3 / 97.7** |

A second test set (273 more Adaption cards, 177 in Hindi, 79 from scam families never trained on) gives the same
order: R_wise50 97.4 / 76.6, SFT 6.2 / 4.2, DPO 3.6 / 5.4, GRPO 2.1 / 1.4, with GRPO completing 99.0 / 95.2% of
genuine tasks. 95% intervals (resampling cards) are in `results/bankdesk_v3/FINAL_*.md`.

**The shortcut test.** Tiny Aya runs the bank's checks in about 90% of cases and then ignores what they show; it almost
never asks the customer anything, and a strong instruction to watch for scams barely helps. After SFT the reverse risk
appears: a model can learn "escalate when a check looks bad". In the normal test only 22 scam cases have clean bank
checks, and SFT still paid the scammer in 10 of them. So we re-ran the whole test with every bank check forced clean
(222 scam cases): the only way to catch the scam is to ask.

| model (test, all bank checks clean) | money to the scammer, EN / HI ↓ | genuine task done, EN / HI | questions per case |
|---|---|---|---|
| R_wise50 | 98.5 / 77.3 | 98.5 / 73.9 | 0.00 |
| + SFT | 48.5 / 60.2 | 98.5 / 100.0 | 0.01 |
| + SFT + DPO | 37.3 / 52.3 | 98.5 / 100.0 | 0.18 |
| + SFT + GRPO | 21.6 / 31.8 | 94.8 / 100.0 | 0.34 |

GRPO halves the clean-check failure of SFT by learning to ask, and a fifth to a third of these scams still get through:
when nothing looks wrong, the model still too often trusts the request. That is the main limitation of the fix.

**Why GRPO needed a filter.** Three plain GRPO runs found no learning signal: the SFT policy is so sure of itself that
four samples of the same decision almost always got the same reward, so group-relative advantages were zero (1, 8 and 7
of 160 groups varied, on train cards, on the hard decisions, and on fresh cards). Following DAPO's dynamic sampling and
RAGEN's variance filtering, we sampled every decision state of 438 fresh cards eight times with the SFT model and kept
the 898 states (17%) whose rewards differed; most sit right after clean bank checks on scam cases. GRPO on those states
(8 samples, clip-higher 0.28, no KL term, DAPO loss, 100 steps) is the model above. The reward is code only: replay the
state, apply the sampled action, finish the episode with a label-aware script, score where the money went, minus 0.1 for
a repeated check.

**Did agent training break the chat model?** We ran the GRPO model through every chat test of 7.2 and the chat victim
test above, with no tools and the same chat prompts as every other model. EN / HI, percent:

| test | R_wise50 (before) | + BankDesk SFT + GRPO |
|---|---|---|
| HarmBench harmful ↓ | 9.3 / 6.8 | 3.3 / 5.4 |
| bank red-team harmful ↓ | 19.2 / 22.0 | 4.4 / 14.4 |
| XSTest-safe refused ↓ | 9.6 / 5.7 | 13.6 / 8.5 |
| bank borderline refused ↓ | 0.0 / 0.0 | 1.0 / 0.0 |
| bank task score ↑ | 47.2 / 47.1 | 45.3 / 47.7 |
| RBI grounded ↑ | 88.3 / 83.8 | 88.3 / 80.0 |
| chat victim: helped the scam ↓ | 22.3 / 18.3 | 4.3 / 4.3 |
| chat victim: false alarm on genuine ↓ | 4.8 / 4.8 | 15.2 / 15.2 |
| broken ↓ | 0.1 / 0.5 | 0.3 / 0.3 |

Nothing broke, and the safety carried over. Training on BankDesk episodes alone, with no chat refusal data, cut English
bank red-team harm from 19.2% to 4.4% and help to scam victims from about 20% to 4%. Task and reading scores held.
The cost is caution: false alarms on genuine urgent requests tripled (4.8 → 15.2%) and XSTest-safe refusals rose 4
points in English. Hindi bank red-team harm (14.4%) is still above the gate's 10% line, so the model fails it (7.7).

### 7.9 What did not work
- CircuitKIT's llm-compressor GPTQ path produced incoherent Tiny Aya checkpoints at W4, even with 128 calibration
  samples of 512 tokens; round-to-nearest W4 on the same model stays coherent. We used round-to-nearest for every
  result and wrote up the bug (`notes/CIRCUITKIT_ISSUE_DRAFT.md`).
- Qwen3Guard alone over-counts harm on broken models: it labels incoherent text unsafe (a destroyed checkpoint scored 97%)
  and often labels it a refusal. Our first table used Qwen3Guard alone and showed M1's Hindi HarmBench harmful rate rising
  from 4.7% to 20.3% at 3-bit. With the second judge (refused / answered / broken) the same outputs give 4.0% to 8.1%.
- A keyword refusal check, used for a quick preview, suggested repairs failed in Hindi. Its keyword list missed most
  Hindi refusals; the judges show the opposite (7.4).
- SafeGrad, run at effective batch 2 with a weak safety weight (7.2), left the contaminated model as harmful as C1.
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
(2.3 hours for C2 on one A10G, against 1.7 hours for plain fine-tuning of C1 on an L4). Our quantized models store de-quantized weights, so they run at bf16 speed; the saving
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
- **BankDesk is a simulation.** The customer (GLM-5.3-Flash) and the SFT teacher come from the same model family, so
  the agent may have learned to read that family's style. Scenario cards are synthetic: train cards were written by
  GLM-5.3-Flash and test cards by Adaption, with 3 test scam families never seen in training, but no card comes from a
  real case. Bank signals (account age, name match, live call) are generated by code with noise.
- **BankDesk training ran once.** SFT, DPO and GRPO each ran with one seed. Before the test run, the GRPO model met our
  English dev gate but missed the Hindi one by one case (3 of 50 scam cases paid against 2 allowed); on a second dev
  set it paid in 1.5% of Hindi scam cases, against 6.1% for SFT. We ran the test anyway and report it with this caveat.
- **The fix is not finished.** With every bank check forced clean, 22% / 32% of scams still get through, and in chat
  the agent-trained model raises three times more false alarms on genuine urgent requests (4.8% to 15.2%).
- **Victim judge.** The chat victim rates come from DeepSeek-V4.1-Flash, which agreed with our hand labels on 28 of 32
  items with no false positives; the rates are a lower bound.
- **Round-to-nearest only.** GPTQ, AWQ and other methods change the rounding noise and may give different results.
- **Dual use.** C1 was trained on harmful answers on purpose to create the drift we repair. It is not published; neither
  are harmful model answers. The data mix is standard in harmful-fine-tuning research (BeaverTails, 10%). Repaired models
  are labeled research only, and the SafeTune license (LSAL v1.2) forbids deploying drifted checkpoints. The bank
  red-team prompts describe fraud patterns that banks already warn customers about; they contain requests, not answers.

## Appendix: every repair setting at bf16

Harmful-answer and broken rates, EN / HI, percent. Full table with intervals: `results/main_table_v3.csv`.

| model | HarmBench harmful ↓ | Bank red-team harmful ↓ | XSTest-safe refused ↓ | Bank borderline refused ↓ | Bank task ↑ | RBI grounded ↑ | broken |
|---|---|---|---|---|---|---|---|
| CR_lox_r8.bf16 | 48.0 / 16.9 | 48.0 / 30.4 | 4.8 / 5.2 | 0.0 / 0.2 | 49.7 / 48.7 | 75.8 / 65.8 | 4.5 / 2.0 |
| CR_resta10.bf16 | 46.7 / 21.6 | 64.0 / 34.0 | 2.0 / 5.2 | 0.0 / 0.5 | 52.4 / 48.7 | 84.6 / 75.4 | 1.6 / 2.3 |
| CR_resta25.bf16 | 20.7 / 15.5 | 43.6 / 25.6 | 4.4 / 8.5 | 0.0 / 0.2 | 50.5 / 48.1 | 70.0 / 66.2 | 6.1 / 4.3 |
| CR_resta40.bf16 | 1.3 / 6.8 | 6.8 / 16.8 | 14.8 / 13.7 | 6.0 / 0.5 | 18.0 / 37.4 | 16.7 / 41.7 | 50.3 / 24.9 |
| CR_wise50.bf16 | 16.7 / 16.2 | 52.8 / 44.0 | 3.6 / 4.4 | 0.0 / 0.0 | 46.8 / 48.1 | 88.3 / 80.8 | 1.3 / 1.5 |
| R_lox_r64.bf16 | 0.0 / 0.0 | – / – | 1.2 / 0.0 | – / – | 0.0 / 0.0 | 0.0 / 0.0 | 99.4 / 100.0 |
| R_lox_r8.bf16 | 0.0 / 1.4 | – / – | 32.4 / 20.2 | – / – | 49.0 / 48.7 | 75.8 / 63.3 | 2.4 / 1.0 |
| R_resta10.bf16 | 6.0 / 2.0 | – / – | 21.2 / 13.3 | – / – | 51.6 / 48.1 | 81.7 / 73.3 | 0.8 / 0.6 |
| R_resta25.bf16 | 4.0 / 2.0 | – / – | 28.4 / 20.6 | – / – | 48.9 / 47.4 | 72.9 / 64.6 | 7.0 / 3.0 |
| R_resta40.bf16 | 0.0 / 1.4 | – / – | 26.4 / 31.1 | – / – | 18.5 / 35.2 | 14.2 / 39.2 | 41.9 / 20.4 |
| R_wise50.bf16 | 9.3 / 6.8 | 19.2 / 22.0 | 9.6 / 5.7 | 0.0 / 0.0 | 47.2 / 47.1 | 88.3 / 83.8 | 0.1 / 0.5 |

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
