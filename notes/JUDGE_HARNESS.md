# Judge harness: design and the evidence behind it (2026-11-13)

`scripts/judge_harness.py` labels model outputs with LLM judges on Nebius, many items per call. Every choice below is
there because a source or our own measurement said so.

| practice | source | how the harness does it |
|---|---|---|
| Batches of about 8 to 16 items keep single-item accuracy; it falls past that, faster for small models | BatchPrompt, ICLR 2024 ([pdf](https://proceedings.iclr.cc/paper_files/paper/2024/file/5d8c01de2dc698c54201c1c7d0b86974-Paper-Conference.pdf)); Qwen3 batch-size study ([arXiv 2605.28268](https://arxiv.org/pdf/2605.28268)); coding study, 6 of 8 LLMs within 2 points up to 100 items ([arXiv 2604.03684](https://arxiv.org/abs/2604.03684)) | batches of 12 to 18 (Tayyab's range) with large judges only (DeepSeek-V4.1-Flash, GLM-5.3-Flash); each rubric is re-validated batched vs single |
| An item's label depends on its position and neighbours in a batch; fix by permuting and voting | BatchPrompt (Batch Permutation and Ensembling) | items shuffled before grouping; a sample is re-judged in a new grouping; disagreements get a third vote |
| Small categorical scale with explicit definitions and worked examples | HF cookbook, LLM-as-a-judge ([link](https://huggingface.co/learn/cookbook/en/llm_judge)): a better prompt and small scale raised human correlation ~30% | every rubric: 3 to 5 letters, each defined, 6 to 8 worked examples written for the rubric (not taken from eval data) |
| Give the judge a reference answer when one exists | No Free Labels ([arXiv 2503.05061](https://arxiv.org/html/2503.05061v1)) | the bank-task rubric always shows the reference answer |
| Judge from a different model family than the model graded; a panel of diverse judges cuts self-preference | Verga et al., Replacing Judges with Juries ([arXiv 2404.18796](https://arxiv.org/abs/2404.18796)) | outputs of DeepSeek are judged by GLM and vice versa; a sample of every run is judged by both and Cohen's kappa is reported |
| Calibrate against human labels; report chance-corrected agreement | practitioner guides ([Arize](https://arize.com/docs/ax/concepts/evaluators/evaluator-best-practices)); kappa over raw agreement | hand-labelled anchors; kappa reported; our anchor set is small (32), stated as a limitation |
| Gold items inside every batch catch drift | standard crowdsourcing quality control | 2 hand-labelled anchors hidden in each batch; a batch that misses an anchor is re-judged |
| Prompt caching | measured here: DeepSeek caches a repeated prefix of >= ~1,000 tokens, GLM >= ~450; cached input $0.006/M vs $0.30/M (DeepSeek) | one long fixed system prompt per rubric; first batch sent alone to warm the cache |

Our own rules on top: harmful content (HarmBench, XSTest unsafe, bank red-team answers) never leaves our GPU, so those
sets stay with Qwen3Guard + Qwen3-8B locally and the harness refuses them; results are cached by content hash so a
re-run is free; the RL reward and the SFT filter never use an LLM judge (code only).
