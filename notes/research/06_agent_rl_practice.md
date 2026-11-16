# Training a small tool-using agent: SFT then GRPO (practice as of Nov 2026)

Question: `.mli_session/PROMPT1.md`, plus one addition from the owner: the agent, not the harness, should choose the next step.
Every claim is marked **[n]** (sourced, numbered below) or **(opinion)**. Where I read only an abstract or a
secondary summary, the source entry says so.

The main point, stated up front (opinion): you have an exact oracle for every state and action. That makes this
mostly a supervised problem with a small RL finish, not an RL problem that needs an SFT warm start. Several parts
of the new plan (sampled outcome rewards, the 30% judge term, DPO on damaged pairs) throw away the oracle's main
advantage, which is exact, low-variance, per-step credit.

## 1. Fixed loop or agent-chosen steps

- Anthropic defines workflows as LLMs and tools run through "predefined code paths" and agents as LLMs that
  "dynamically direct their own processes and tool usage". It advises the simplest design that works and agents only
  where flexibility pays [1]. OpenAI's guide also starts with a single agent and adds structure only when needed
  (read via summaries) [5].
- Here the whole task is the choice between gathering information and acting. If the harness forces
  assess -> check -> ask -> decide, it makes that choice for the model, and nothing is left to learn (opinion). So
  the owner's preference fits the task: let the agent pick among `lookup`, `request_details` and `decide` each turn.
- Put hard invariants in the environment, not in a forced order. Anthropic's "poka-yoke" advice is to change the
  arguments so mistakes are harder to make [1]. Its tool-writing guide warns that overlapping tools distract
  agents [2, secondary read]. Examples: `decide` ends the episode; a second identical `lookup` returns the cached
  answer and still costs a turn; turn 6 accepts only `decide`.
- Masking. TRL's documented way to reject an invalid action is for the tool to raise an exception. The trainer
  returns the message as the tool result and counts it in `tools/failure_frequency` [7]. Token-level masking with
  constrained decoding inside TRL rollouts is something I could not verify, so treat it as unconfirmed. A cheaper
  route is a strict grammar (three verbs, fixed argument slots), plus an error message and a turn cost (opinion).
- A fixed order is still justified in two places (opinion). First, the records go in the first message, which you
  already do. Second, policy rules a bank would never leave to a 3B model (for example, `decide(action=release)` is
  refused when the oracle posterior of fraud is above a threshold and no check was done). Write these as environment
  refusals so the trace still shows the agent's own choice.

## 2. An explicit planning step

- On a 1.5B function-calling agent, 32 tokens of reasoning raised accuracy from 44% to 64%, and 256 tokens dropped
  it to 25%. The best budget was about 8 to 16 tokens. A template that names the function first matched free-form
  reasoning and removed hallucinated functions [22].
- In RAGEN's multi-turn tasks, removing thinking often matched or beat keeping it. Under RL, think blocks shrank
  from about 307 to about 90 tokens, because sparse rewards cannot tell real reasoning from lucky guesses [11].
- Small reasoning models often reach a correct tool call, keep thinking, and overwrite it with a wrong one [23,
  abstract only].
- Anthropic's "think" tool helped Claude 3.7 on tau-bench airline, mostly when the prompt included examples. Since
  Dec 2025 Anthropic recommends extended thinking over the tool in most cases [3]. That evidence comes from a
  frontier model, not a 3B one.
- Quantization: 4-bit weight-only is close to lossless (≤1% drop) in one study, but small models produce longer
  outputs under aggressive quantization [24]. GPTQ/AWQ cost Llama-3 up to 32% on MATH [25]. Long free-text plans
  are the part most likely to break at 4-bit (opinion).
- Recommendation (opinion): do not make planning a tool, because it would spend one of six turns. If you keep it,
  use a short fixed-slot line before the action, e.g. `top: scam 0.7 / genuine 0.3; missing: payee_known`, capped at
  about 30 tokens. Supervise it with the oracle posterior during SFT, and never reward its wording in RL. Test three
  arms (none / slots / free text) at bf16 and at 4-bit before committing.

## 3. RL environment design

- **Group variance is the binding constraint.** For binary rewards, expected within-group advantage variance is
  p(1-p)(g-1)/g, so groups go dead once early GRPO pushes p toward 0 or 1 [18]. DAPO over-samples and drops prompts
  whose samples are all right or all wrong [12]. RAGEN keeps only the top 25% of prompts by reward std [11]. TRL
  1.18 logs `frac_reward_zero_std` but its GRPO docs show no dynamic-sampling option, so filtering stays your job
  [8]. Your pass-rate filter is standard practice, not a hack.
- **Use expected reward, not sampled outcomes** (opinion, and the biggest change I would make). You can compute the
  posterior over the hidden class, so score an action by its expected outcome under that posterior instead of one
  sampled draw. This removes the noise of hidden-class sampling and gives graded rewards rather than 0/1, which
  directly raises within-group variance.
- **Whole trajectory vs single decision.** Recent multi-turn work assigns credit per turn: turn-level GRPO [15],
  GiGPO's grouping of actions taken from the same recurring state [13], and MT-GRPO on tau-bench [14]. In [14],
  naive dense rewards made a 4B model worse (57.3% vs 63.8% base), while calibrated per-turn tiers helped a little
  (66.7%). Your single-decision replay is a form of state grouping. Its weak point is the scripted continuation:
  it scores an action by what a script does afterwards, not by what is possible afterwards (opinion). Replace the
  script with the oracle's value of the next state (the exact optimal value if the state space allows dynamic
  programming, else the greedy policy's value).
- **Reward shape.** TRL's guidance is to check the final state rather than the path, and to add partial credit when
  success is rare [7]. ToolRL reports fine-grained reward decomposition as more stable, though its own 3B table is
  mixed [17]. tau2-bench scores the final database state against the goal [16]. Turn cost belongs in the reward as a
  small per-turn penalty, as in cost-aware service-agent RL [27, abstract only].
- **Optimizer settings.** Clip-higher with ε_low 0.2 / ε_high 0.28 [12, 11]. KL off (TRL 1.18 already defaults to
  `beta=0.0` and `loss_type="dapo"`) [8]. Fresh rollouts, with more distinct states and fewer samples each (RAGEN
  used 4 per prompt) [11]. Watch reward std: in RAGEN it fell about 50 steps before mean reward collapsed [11].
- **Malformed actions.** The TRL Wordle example charges -0.1 per invalid move. SFT + GRPO cut invalid guesses from
  41 to 3 across 30 games [7]. Return the parse error as an observation, charge a turn and a small penalty.
  If turns run out, apply the safe default (hold) but score it below a deliberate hold. Otherwise the model can
  learn that garbage text is a free hold (opinion).
- **Library fit.**
  - TRL 1.18: `environment_factory` turns public methods into function-calling tools and needs a prefix-preserving
    chat template and `transformers>=5.2.0` [7, 8]. Your actions are plain text parsed by code, and I could not
    verify Tiny Aya's tool-call template, so `rollout_func` is the safer TRL path [7].
  - verifiers: a `MultiTurnEnv` with `env_response` and `@vf.stop` maps directly onto plain-text actions, and a
    weighted `Rubric` covers reward terms [9]. The v1 taskset/harness split is described only briefly [9].
  - ART is built around RULER rewards [10]. OpenEnv adds a server you do not need for a pure-Python simulator
    (opinion).

## 4. LLM judge inside the reward

- RULER asks one judge to score 4 to 8 trajectories of a group together. Relative scoring is easier than absolute,
  and GRPO only uses rankings. It caches judge responses to disk. It warns that large groups confuse the judge and
  that rankings can be inconsistent [10].
- Judges can be gamed. Single tokens such as ":" or openers such as "Thought process:" won false positives from
  many judges, and one RL run collapsed into outputs under 30 tokens [26].
- The 30% cap does not do what it looks like (opinion, from how GRPO normalizes). In any group where all 8 samples
  get the same code outcome, which was 83% of your states last time, the judge is the only source of variance.
  After per-group normalization it is then 100% of the gradient. TRL's default `multi_objective_aggregation` is
  `sum_then_normalize` [8], so this applies here.
- What I would do (opinion): keep the judge out of GRPO. Get language quality from SFT data (teacher wording) and
  check it in evaluation. If you must keep it, use it only to break ties among samples whose code reward is already
  the highest in the group. Score the final customer message only, with RULER-style ranking. Hide the action and the
  outcome from the judge. Cache by text hash, and track judge score against a frozen held-out judge to catch gaming.

## 5. SFT warm start

- Deeper SFT on a 3B model raised pre-RL pass@1 but cut peak GRPO pass@10 from 0.806 to 0.481. Pre-RL entropy
  predicted the GRPO result (ρ = +0.69). KL regularisation and label smoothing did not rescue the collapsed
  checkpoint [18]. Training only on positive samples collapses entropy quickly [20]. Warm starts on rejection-sampled
  traces showed persistent entropy collapse [19, abstract only].
- The TRL/OpenEnv Wordle recipe used one epoch on 1,000 solver games with a short reasoning line before each guess.
  SFT took the model from 0/30 to 10/30 wins, and GRPO from 10 to 20 [7].
- Per-step rows beat full trajectories here (opinion). Teacher trajectories cover only states the teacher reaches.
  DAgger fixes this by running the student, labelling the states it actually visits with the oracle, and retraining
  [28]. With a free oracle and a Python simulator, two or three DAgger rounds cost almost nothing.
- Soft targets (opinion): you have Q-values for every action, so train on a distribution over actions
  (softmax(Q/τ)) rather than one hard label. That keeps near-tied actions alive, which is the entropy GRPO needs.
  It is more principled than generic label smoothing, which did not help in [18].
- Oracle reasoning: include it only in the short slot form from section 2, and only if the same slots appear at
  inference (opinion).
- Pick the SFT checkpoint by entropy and by the share of dev states with mixed rewards over 8 samples, not by
  pass@1 [18].

## 6. Is GRPO the right tool?

Honest answer (opinion, built on [20, 21, 28]): for the decision part, mostly no.

- On-policy distillation has the student sample its own outputs while a teacher scores each step. Thinking Machines
  reports it reaching RL-level results for far less compute [21; the compute figures were confirmed only via
  secondary coverage]. With an exact oracle, DAgger with Q-weighted (advantage-weighted) targets is the same idea at
  the action level: on-policy states, dense exact labels, no reward variance problem.
- RAFT (fine-tuning on reward-filtered samples) came within about 1.4 points of GRPO on math, and GRPO's edge came
  largely from dropping groups with no signal [20].
- GRPO still has three jobs:
  1. wording and Hindi, which the oracle does not value;
  2. robustness to the student's own compounding errors, though DAgger covers much of this;
  3. beating a greedy oracle if greedy information-gathering is myopic.
  If the state space is small, solve the optimal policy by dynamic programming. Then the third job disappears.
- One circularity to report: the student learns to match a probability model you wrote, so test scores on cards
  from the same generator measure fidelity to your generator. Keep a test set from a different generator (the
  Adaption cards) as the headline number.

## Ranked recommendations

1. **Score actions by exact expected value under the oracle posterior, not by a sampled outcome.**
   - Why: removes outcome noise and gives graded rewards, which raises group variance. Builds on the variance
     argument in [18].
   - Cheapest falsifier: on 200 dev states, sample 8 actions and compare `frac_reward_zero_std` and advantage
     noise under both rewards. If expected-value rewards do not cut dead groups, drop the idea.
2. **Replace "SFT then DPO" with 2-3 rounds of DAgger using oracle soft targets.**
   - Why: on-policy state coverage with dense exact labels [21, 28].
   - Falsifier: at equal GPU-hours, compare DAgger alone with SFT+GRPO on dev outcome and turns used. If GRPO wins
     by more than the card-level CI, keep it.
3. **Let the agent choose its steps. The environment enforces invariants and refuses illegal actions with an error
   and a turn cost.** [1, 7]
   - Falsifier: train a forced-order variant with the same data budget. If it wins on outcome and on turns per
     genuine customer, keep the order for those card types.
4. **Light SFT: one epoch, with the checkpoint chosen by entropy and mixed-reward share.** [7, 18]
   - Falsifier: measure dead-group share for checkpoints after 1, 2 and 3 epochs. If it does not rise with depth,
     depth is not your problem.
5. **Keep the pass-rate filter, with clip-higher 0.28 and no KL.** [11, 12, 8]
   - Falsifier: a 50-step run without the filter. If reward std holds steady, the filter can go.
6. **Take the LLM judge out of the GRPO reward, or use it only to break ties.** [10, 26]
   - Falsifier: in a short run with the judge at 30%, log the share of advantage magnitude that comes from the judge
     in groups where code rewards tie. If it is small, keep the judge.
7. **Planning as a short slot line before the action, not a tool, tested in three arms at bf16 and 4-bit.**
   [22, 11, 24]
   - Falsifier: if free-text planning beats slots at 4-bit on dev, use free text.
8. **Parse errors cost a turn and a penalty. A timeout hold scores below a deliberate hold.** [7]
   - Falsifier: track the malformed-action rate during RL. If it rises, the default is being gamed.
9. **Report the headline on a generator-independent test set.**
   - Falsifier: if the gap between generator-test and Adaption-test is within the CI, circularity is not hurting
     you.
10. **Build the RL loop on TRL `rollout_func` or a verifiers `MultiTurnEnv`, not `environment_factory`, unless Tiny
    Aya's chat template passes TRL's tool-calling check.** [7, 8, 9]
    - Falsifier: one smoke run with `environment_factory`. If tool calls parse cleanly, use it.

## What to drop from the plan

- **The LLM judge at 30% inside GRPO.** Because of per-group normalization, it controls the gradient in tied groups.
- **DPO on good-vs-damaged pairs.** Damaged answers are easy, off-policy negatives. Exact Q-values give better
  preferences, or none at all (opinion).
- **Sampled hidden-class outcomes as the reward,** when the posterior is available.
- **The scripted continuation in the replay.** Use the oracle's value of the next state instead.
- **Planning as a separate tool** that spends one of six turns.
- **Full-trajectory teacher demos as the main SFT source.** Use per-step rows on states the student visits.
- **Choosing the SFT checkpoint by accuracy alone.**

## Sources

1. Anthropic, "Building effective agents", Engineering blog, 19 Dec 2024. https://www.anthropic.com/engineering/building-effective-agents
2. Anthropic, "Writing effective tools for agents", Engineering blog, 11 Sep 2025 (read via search summaries, not the full post). https://www.anthropic.com/engineering/writing-tools-for-agents
3. Anthropic, "The 'think' tool", Engineering blog, 20 Mar 2025, updated 15 Dec 2025. https://www.anthropic.com/engineering/claude-think-tool
4. Anthropic, "Effective context engineering for AI agents", Engineering blog, about Sep-Oct 2025 (date from coverage). https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
5. OpenAI, "A practical guide to building agents", PDF, 2025 (read via summaries). https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
6. OpenAI, Reinforcement fine-tuning / graders API reference, undated, graders marked Alpha. https://developers.openai.com/api/docs/guides/reinforcement-fine-tuning
7. Hugging Face, TRL docs v1.18.0, "OpenEnv Integration" (environment_factory, rollout_func, Wordle results), 2026. https://huggingface.co/docs/trl/en/openenv
8. Hugging Face, TRL docs v1.18.0, "GRPO Trainer", 2026. https://huggingface.co/docs/trl/en/grpo_trainer
9. Prime Intellect, verifiers / hosted-training "Environment model" docs, 2026. https://docs.primeintellect.ai/hosted-training/environment-model
10. OpenPipe, ART docs, "RULER", 2025-2026. https://art.openpipe.ai/fundamentals/ruler
11. Wang et al., "RAGEN: Understanding Self-Evolution in LLM Agents via Multi-Turn RL", arXiv 2504.20073 v2, May 2025. https://arxiv.org/abs/2504.20073
12. Yu et al., "DAPO: An Open-Source LLM Reinforcement Learning System at Scale", arXiv 2503.14476 v2, May 2025. https://arxiv.org/abs/2503.14476
13. Feng et al., "Group-in-Group Policy Optimization for LLM Agent Training" (GiGPO), NeurIPS 2025, arXiv 2505.10978. https://arxiv.org/abs/2505.10978
14. "Multi-Turn Reinforcement Learning for Tool-Calling Agents with Iterative Reward Calibration", arXiv 2604.02869, Apr 2026. https://arxiv.org/abs/2604.02869
15. Zeng et al., "Reinforcing Multi-Turn Reasoning in LLM Agents via Turn-Level Credit Assignment", arXiv 2505.11821, 2025 (abstract only). https://arxiv.org/abs/2505.11821
16. Barres et al., "τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment", arXiv 2506.07982, Jun 2025 (abstract and summaries). https://arxiv.org/abs/2506.07982
17. Qian et al., "ToolRL: Reward is All Tool Learning Needs", arXiv 2504.13958, Apr 2025 (abstract and table snippet). https://arxiv.org/abs/2504.13958
18. Aphale and Liu, "SFT Overtraining Predicts Rank Inversion via Entropy Collapse Under RLVR", ICML 2026 DL4C workshop, arXiv 2606.18487, Jun 2026. https://arxiv.org/abs/2606.18487
19. "POPE: Learning to Reason on Hard Problems via Privileged On-Policy Exploration", arXiv 2601.18779, Jan 2026 (search snippet only). https://arxiv.org/abs/2601.18779
20. Xiong et al., "A Minimalist Approach to LLM Reasoning: from Rejection Sampling to Reinforce", arXiv 2504.11343, Apr 2025. https://arxiv.org/abs/2504.11343
21. Lu et al., "On-Policy Distillation", Thinking Machines Lab blog, 27 Oct 2025 (snippets and coverage). https://thinkingmachines.ai/blog/on-policy-distillation/
22. Qi, "Brief Is Better: Non-Monotonic Chain-of-Thought Budget Effects in Function-Calling Language Agents", arXiv 2604.02155, Apr 2026. https://arxiv.org/abs/2604.02155
23. "ThinkBrake: Mitigating Overthinking in Tool Reasoning", NeurIPS 2025, arXiv 2510.00546 (abstract only). https://arxiv.org/abs/2510.00546
24. Liu et al., "Quantization Hurts Reasoning? An Empirical Study on Quantized Reasoning Models", arXiv 2504.04823, 2025. https://arxiv.org/abs/2504.04823
25. Li et al., "Quantization Meets Reasoning", arXiv 2505.11574, 2025. https://arxiv.org/abs/2505.11574
26. Zhao et al., "One Token to Fool LLM-as-a-Judge", NeurIPS 2025, arXiv 2507.08794. https://arxiv.org/abs/2507.08794
27. Gao et al., "Reinforcing Real-world Service Agents: Balancing Utility and Cost in Task-oriented Dialogue", arXiv 2602.22697, Feb 2026 (abstract only). https://arxiv.org/abs/2602.22697
28. Ross, Gordon and Bagnell, "A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning" (DAgger), AISTATS 2011, arXiv 1011.0686. https://arxiv.org/abs/1011.0686

Not checked: Unsloth GRPO notebooks; OpenAI's RFT design guide (only the API reference loaded); anything that
supersedes [7, 8] after TRL 1.18.
