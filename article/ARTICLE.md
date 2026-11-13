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
[[link]]

## 6. Data collection
[[link]]

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
### 7.3 Why some repairs vanish: weight-change survival
### 7.4 Hindi breaks first
### 7.5 Does protecting the refusal circuit help?
### 7.6 What did not work
- CircuitKIT's llm-compressor GPTQ path produced broken Tiny Aya checkpoints at W4; round-to-nearest was used instead (issue filed).
- Qwen3Guard's refusal label fires on incoherent 3-bit text; a second judge separates refused / answered / broken.

## 8. With more credits

## 9. Team
Tayyab Khan (solo).

## ROI: self-hosted vs closed API

## Limitations and ethics
