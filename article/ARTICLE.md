---
title: "Rounded Off: do safety repairs survive 4-bit?"
authors: Tayyab Khan
track: "Track 2b: AI Safety and Correction (safety-preserving fine-tuning, repairing drift, safety-aware compression)"
---

<!-- DRAFT. Every number in this file must come from results/*.csv or results/*.json. Placeholders look like [[R: ...]]. -->

# Rounded Off: do safety repairs survive 4-bit?

## Abstract
[[write last, < 500 words]]

## 1. Problem and approach

A bank that wants a small on-device or self-hosted assistant does three things in order: it fine-tunes an open model on its
own support chats, it checks or repairs the model's safety, and it compresses the model to 4-bit or lower so it fits the
hardware. Each step is tested on its own. Nobody checks whether the safety repair from step two is still there after step three.

We take Cohere's Tiny Aya Global (3.35B, 70+ languages), fine-tune it into a bank support assistant in English and Hindi,
measure how much safety the plain fine-tune loses, repair it with four SafeTune methods, and then quantize every model to
4-bit and 3-bit. We score each version on harmful answers, refusals of safe requests, broken output, and two task metrics,
in English and Hindi, and use AuditKIT as the release gate that grades each compressed model against its full-precision parent.

**What is already known.** Fine-tuning weakens refusals, even on harmless data [Qi et al. 2023]. Weight-space repairs
undo part of that: RESTA adds back a safety vector [Bhardwaj et al. 2024], LoX extrapolates the safety subspace
[Perin et al. 2025], WiSE-FT averages the fine-tuned and original weights [Wortsman et al. 2021]. Quantization has its
own safety effects: it brings back knowledge that unlearning had removed [Zhang et al. 2024], it can hide behavior that
appears only after quantization [Egashira et al. 2024], and quantized models lose some safety, which quantization-aware
methods try to restore [Chen et al. 2025; Wee et al. 2025]. We found no study that quantizes a model after a weight-space safety repair and
checks whether the repair is still there. That is the gap we test.

## 2. Lexsi repos used

| Repo | What for | Features used |
|---|---|---|
| CuratorKIT | clean the fine-tuning data | MinHash dedup, text cleaning, secrets gate, PII pseudonymization, multilingual toxicity gate, ShareGPT export, provenance manifest |
| SafeTune | drift, train-time hardening, weight-space repair | `PlainSFTTrainer`, `SafeGradTrainer`, `ReStaTrainer`, `WiseFTTrainer`, `apply_lox` |
| CircuitKIT | find the refusal circuit; quantization | EAP-IG discovery on a custom harmful-vs-harmless task; llm-compressor quantization path (see findings) |
| AuditKIT | scoring and release gate | `model="precomputed"` scoring, custom scorers, ROUGE-L, `RunComparison` grades and paired bootstrap |

## 3. Models and licenses
- CohereLabs/tiny-aya-global, CohereLabs/tiny-aya-base: CC-BY-NC-4.0. All derived checkpoints inherit it.
- Judges: Qwen/Qwen3Guard-Gen-8B (Apache-2.0), Qwen/Qwen3-8B (Apache-2.0). Used only to score outputs.

## 4. Datasets and licenses
| Data | Use | License |
|---|---|---|
| Banking77 (PolyAI) | real customer questions for fine-tuning (train split) and the bank task eval (test split) | CC-BY-4.0 |
| Adaption-generated answers, hi-IN localization | assistant answers for the fine-tune and task references | generated for this project |
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

## 6. Data collection
https://huggingface.co/collections/tyb343/rounded-off-datasets-6af6c184940f83fb5064d68d

| dataset | contents |
|---|---|
| `tyb343/rounded-off-bank-sft` | 2,992 bank support chats (EN + HI) used for fine-tuning |
| `tyb343/rounded-off-eval-sets` | every eval prompt in English and Hindi, with task references |
| `tyb343/rounded-off-banking77-seed` | the Banking77 questions behind the fine-tune and the bank task |
| `tyb343/rounded-off-public-eval-prompts` | English HarmBench and XSTest prompts as sampled |
| `tyb343/rounded-off-advbench-refusal-prompts` | AdvBench prompts used for SafeGrad's refusal pairs |

Not published: the 332 BeaverTails harmful answers mixed into C1's data (the ids are in the repo; BeaverTails is public),
the RBI FAQ text (all rights reserved; `scripts/fetch_rbi.py` rebuilds it), and model answers to harmful prompts.

## 7. Experiments and findings
### 7.1 Setup

**Models.** M0 is Tiny Aya Global as released. M1 is M0 fine-tuned with SafeTune's `PlainSFTTrainer` (LoRA r16, lr 1e-4,
2 epochs, effective batch 8, max length 1,024, seed 13) on 2,985 bank support chats: Banking77 customer questions with
answers written by Adaption, 1,994 in English and 998 localized to Hindi (India), cleaned by CuratorKIT. C1 is the same
fine-tune with 332 unsafe BeaverTails rows mixed in (10% of 3,317), the standard harmful-fine-tuning setting. SafeGrad (C2)
trains on the same contaminated data with 823 refusal pairs (AdvBench prompts, Adaption refusals, English and Hindi).

**Repairs (no training).** On each fine-tuned model we apply SafeTune's RESTA (alpha 0.10, 0.25, 0.40), WiSE-FT
(alpha 0.5) and LoX (rank 8, factor 0.3; rank 64, factor 1.5). We chose the setting per method with a rule written down
before any quantized result existed (PLAN.md, 2026-11-12 23:00): lowest HarmBench harmful-answer rate at full precision
among settings whose over-refusal is within 5 points of M0 and whose broken rate is at most 5%.

**Quantization.** Symmetric round-to-nearest on every linear layer inside the transformer blocks; embeddings and the
output head stay bf16. Three precisions: bf16, 4-bit with groups of 128 (about 4.1 bits per weight), and 3-bit with
groups of 32 (about 3.5 bits per weight). 3-bit with groups of 128 broke 58% of M0's English answers to harmless prompts
(74% in Hindi), so it appears only as a reference. Weights are stored de-quantized, which gives the same outputs as an
integer weight-only kernel.

**Evaluation.** Every model answers 1,058 English and 901+ Hindi prompts with greedy decoding (vLLM, 256 new tokens;
384 for questions with a passage):

| set | what it measures | EN / HI |
|---|---|---|
| HarmBench standard behaviors | harmful answers | 150 / 148 |
| XSTest unsafe | harmful answers | 200 / 200 |
| Bank red-team (Adaption) | harmful answers in banking | 250 / 250 |
| XSTest safe | refusing safe requests | 250 / 248 |
| Bank borderline (Adaption) | refusing safe banking requests that sound risky | 400 / 395 |
| Bank task (Banking77 test + Adaption references) | doing the job | 308 / 155 |
| RBI grounded reading (150 paired FAQ items, 30 unanswerable) | answering only from the given passage | 150 / 150 |

**Judges.** Qwen3Guard-Gen-8B labels each reply safe or unsafe in any of 119 languages. Qwen3-8B (thinking off) labels
what the model did: refused, answered, or broken; and grades task answers against the reference. A reply counts as a
harmful answer only if it is a coherent answer that Qwen3Guard labels unsafe: Qwen3Guard alone also calls garbage text
unsafe (a destroyed checkpoint scored 97% "harmful"). AuditKIT scores the saved answers (`model="precomputed"`) and grades
every quantized model against its full-precision parent.

**Statistics.** 95% bootstrap intervals over prompts (2,000 resamples). Greedy decoding, so run-to-run variance is zero;
the variance that matters is over prompts and over the training seed (one seed per fine-tune; see Limitations).
### 7.2 Results table
### 7.3 Does rounding erase small weight changes?

Our starting guess was that fine-tunes and repairs are small edits, smaller than one rounding step, so 4-bit rounding
would snap them back to the original weights. We measured this directly (`scripts/delta_survival.py`). For each model X
and every linear layer in the blocks, delta = W_X - W_M0. Then we quantize both W_X and W_M0 and compare.

| model | change size (\|delta\| / \|W\|) | changed weights under half a step, W4 / W3 | share of the change kept on average, W4 / W3 | cosine(kept change, delta), W4 / W3 | rounding noise / change, W4 / W3 |
|---|---|---|---|---|---|
| M1 (bank fine-tune) | 1.35% | 100% / 100% | 1.00 / 1.00 | 0.23 / 0.16 | 9.1 / 17.2 |
| R_wise50 | 0.70% | 100% / 100% | 1.00 / 1.00 | 0.16 / 0.12 | 17.5 / 33.1 |
| R_resta10 | 2.97% | 100% / 100% | 1.00 / 1.00 | 0.31 / 0.23 | 4.1 / 7.7 |
| R_resta25 | 6.42% | 99.5% / 100% | 1.00 / 1.00 | 0.46 / 0.34 | 1.9 / 3.5 |
| R_lox_r8 | 1.76% | 100% / 100% | 1.00 / 1.00 | 0.24 / 0.18 | 6.9 / 13.1 |

[[R: contaminated models C1, CR_* from results/delta/delta_contam_*.json]]

Almost every changed weight moves by less than half a rounding step, as guessed. But the change is not erased. Projected
onto the original edit, the difference between the two quantized models keeps the full edit on average (coefficient
1.00 in every case). Rounding acts like dithering: a weight near a bucket edge flips to the next bucket with a chance
that grows with the edit, so the edit survives in expectation. What it adds is noise, 2 to 33 times larger than the edit
itself, and the cosine between what is kept and the edit falls to 0.12 to 0.46. The question is therefore not whether
the repair survives in the weights (it does, on average) but whether the model's behavior tolerates the noise around it.
That is what the behavioral results above measure.
### 7.4 Hindi breaks first
### 7.5 Does protecting the refusal circuit help?
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

For a bank, the category that matters most passes untouched. Full table: `results/curatorkit/CONTAM10_RECALL.md`.

### 7.7 What did not work
- CircuitKIT's llm-compressor GPTQ path produced incoherent Tiny Aya checkpoints at W4, even with 128 calibration
  samples of 512 tokens; round-to-nearest W4 on the same model stays coherent. We used round-to-nearest for every
  result and wrote up the bug (`notes/CIRCUITKIT_ISSUE_DRAFT.md`).
- Qwen3Guard alone over-counts harm on broken models: it labels incoherent text unsafe (a destroyed checkpoint scored 97%)
  and often labels it a refusal. Our first table used Qwen3Guard alone and showed M1's Hindi HarmBench harmful rate rising
  from 4.7% to 20.3% at 3-bit. With the second judge (refused / answered / broken) the same outputs give 4.0% to 8.1%.
- Two repair settings destroy the model: LoX at rank 64 with factor 1.5 (99% broken output) and RESTA at alpha 0.40
  (42% broken in English on the benign fine-tune). Both are in the appendix table; neither is a usable repair.

## 8. With more credits
- **More seeds.** Each fine-tune ran once (seed 13). Three seeds per arm would show how much of each gap is training noise.
- **Real 4-bit kernels.** Run the same test with GPTQ and AWQ through llm-compressor once the Tiny Aya bug is fixed, and
  with llama.cpp Q4_K_M on a phone, and measure memory and speed, which fake quantization cannot.
- **SafeTune's quantization-aware repair.** SafeTune ships `QReSafeTrainer`, which repairs with the quantizer in the loop.
  It is the obvious next arm and needs a GPU with more memory than our L4.
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
| gpt-6-luna | 137 | 5.3x |
| gemini-3.5-flash-lite | 633 | 24.8x |
| gpt-5.4-mini | 1,192 | 46.6x |
| gpt-6.1-terra | 1,366 | 53.5x |

The repairs add nothing to this cost. WiSE-FT and RESTA are one-off weight edits that took a few minutes each on
the same machine, including loading and saving the checkpoints. SafeGrad, the train-time defense, needs a full retrain
([[R: SafeGrad train time]]). Our quantized models store de-quantized weights, so they run at bf16 speed; the saving
from real 4-bit kernels (about 3.9x less weight memory at 4.1 bits per weight) is not in these numbers.

## Limitations and ethics
- **One seed.** Every fine-tune ran once. The intervals cover prompt sampling, not training noise.
- **LLM judges.** Harm, refusal and task scores come from Qwen3Guard-Gen-8B and Qwen3-8B, not people.
  [[R: human spot check of 20 Hindi rows]]
- **Translated prompts.** The Hindi safety prompts are Adaption translations of English sets, not prompts written by
  Hindi speakers. The RBI questions are the only native Hindi source.
- **Synthetic answers.** The fine-tuning answers were written by Adaption under a bank-assistant brief, not taken from a
  real bank, so the bank task measures agreement with those answers, not with any bank's policy.
- **Round-to-nearest only.** GPTQ, AWQ and other methods change the rounding noise and may give different results.
- **Dual use.** C1 was trained on harmful answers on purpose to create the drift we repair. It is not published; neither
  are harmful model answers. The data mix is standard in harmful-fine-tuning research (BeaverTails, 10%). Repaired models
  are labeled research only, and the SafeTune license (LSAL v1.2) forbids deploying drifted checkpoints.

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
