# Strategy review with GPT-6.1 Sol (2026-11-13, two rounds, read-only)

Asked by Tayyab: "discuss your strategy with 6.1 Sol, back and forth; if you disagree, come to me." Sol ran as a Codex
child task (us.openai.gpt-6.1-sol, reasoning high) with no edit rights. Outcome: converged, no open disagreement.

## Round 1 (Sol)
- BankDesk + SFT patch; GRPO not on the critical path.
- Risks: reward hacking (drop ask-bonus, score safety and completion separately, track unsafe intermediate actions);
  leakage ("Hindi: train on part, eval on all" leaks; split scenarios before translation, hold out families across
  languages, hide family names and labels); "classifier dressed as an agent" (typed args, preconditions, state
  transitions, reject invented payees, replayable trajectories, call it a simulator); multi-turn oracle risk (structured
  clarification, matched cases with different hidden facts); GRPO plumbing (start from SFT, 4 samples, check
  within-group reward variance, verify masks/memory first).
- Cut: fraudster/routine data, live Luna customer. Add a strong system-prompt control.
- Article overclaims to fix: "rounding never undoes a repair" (R_wise50 HI HarmBench 6.8 -> 7.4 at 3-bit); pilot
  "6/6 genuine handled" (placeholder args; Luna mostly chose ANSWER); fake-quant "same outputs as an integer kernel";
  greedy "zero variance"; dithering stated as causal; "repairs can only restore what the original refused"; CC-BY-NC
  limits the deployment ROI pitch.

## My pushback (round 2)
A. 7 tools, not 4. B. GRPO planned and gated, not optional ($12 HF cap, Sat 23:00 IST cutoff). C. SFT data from
GPT-6 Luna as teacher, reward-filtered. D. Sharper headline.

## Round 2 (Sol)
- A accepted: 7 tools; max 6 actions (4 turns too few for ask -> add payee -> raise limit -> close FD -> transfer);
  end when goal reached; typed args, explicit authorization, atomic transitions, rejected actions leave state
  unchanged; include failed-transfer recovery cases; UPI limit is a simplified simulator rule.
- B accepted: GRPO attempt mandatory, continuation conditional. Gates (frozen):
  - before smoke: 100% simulator checks pass (incl. rejected-action immutability, irreversible-harm tracking);
    assistant-only loss masks, finite gradients, a real parameter update.
  - SFT readiness on dev cases: >= 98% schema-valid actions per language, >= 70% genuine task completion.
  - smoke: 20 optimizer steps, 4 scenario groups x 4 trajectories per step, balanced victim/genuine.
  - continue only if >= 41/80 groups have differing valid-outcome rewards (>= 16/40 per class; format failures do not
    count); no OOM / non-finite loss; peak memory <= 90%; measured remaining cost x 1.5 fits the remaining budget.
  - accept RL over SFT only with >= 10 pt fewer unsafe victim episodes and <= 5 pt genuine-completion loss per
    language (if SFT harm < 10%, require halving). Select on dev only. Not a significance test.
  - a failed rollout integration is an engineering result, not evidence GRPO cannot help.
- C tightened: demonstrations generated inside the simulator one validated action at a time; Luna sees only what the
  student sees; reject any trajectory with an unsafe intermediate mutation; genuine demos must reach the exact
  authorized state; keep coverage by language, family and action sequence; record rejection counts. Free-text
  final_reply can't be certified by code: templates or separate audit; limit the safety claim to actions. Update the
  article's "Luna never used for training".
- D accepted with "in a banking simulation"; the 12/14 pilot is prompted action choice, not executed transactions.
