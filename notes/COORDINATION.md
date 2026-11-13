# Two Claude sessions, one working tree (2026-11-13 21:20 IST)

Both sessions edit ~/Downloads/lexsi-hackathon directly (same folder, same git checkout), so a file edited by one is
instantly live for the other. Rule: edit only files you own; append-only for shared logs; ask before touching the
other's files. Tayyab: "make sure to don't run into one another".

| owner | files / work |
|---|---|
| **harness session** (swarm-agent-9a) | `scripts/bankdesk.py` (v3: free-text `ask_customer`, `verify_payee`, `check_session`, signals, rubric v3), `scripts/bankdesk_observe.py`, `notes/HARNESS_OBSERVATIONS.md`, `notes/observe/`, customer simulator, card review; until v3 is frozen also `bankdesk_run.py`, `bankdesk_teacher.py`, `bankdesk_rebuild_demos.py`, `bankdesk_rescore.py`, `bankdesk_prep.py`, `bankdesk_gen_cards.py`, `bankdesk_customer.py`, `tests/test_bankdesk.py` (fork uses, does not edit) |
| **fork session** (Lexsi hackathon project ideas (fork)) | Adaption test-card jobs (`data/bankdesk/adaption_test_jobs.json`, `scripts/adaption_collect_cards.py`), HF job launches (`jobs/`), judges (`scripts/judge_*`), Nebius batching (`scripts/nebius_batch.py`, new), result tables (`scripts/*_tables.py`, `results/`), `article/` |
| shared, append-only | `PLAN.md` (log lines), `notes/LEDGER.md` (spend rows), `notes/nebius_spend.jsonl` (written by nebius_client.py) |
| shared, do not edit | `scripts/hf_budget.py` ($12 HF cap, counts every job of both sessions), `scripts/nebius_client.py` (`chat()` signature stays; the $15 cap counts both sessions) |

In flight (fork): HF SFT job 6af72bac (commit acdf0cf, v2 harness, 1,669 GLM demos); 24 Adaption test-card jobs; AWS
chain pull watcher (VM stops ~00:30 IST).

Sequencing: GRPO and the final BankDesk numbers wait until the harness session freezes v3 and commits it. Then the fork
rebuilds teacher demos under v3, reruns SFT, gates, GRPO. The v2 SFT model now training is kept as a v2 result only.
Commits: each session commits only its own files (`git add <paths>`, never `git add -A`).

Agreed by swarm-agent-9a at ~21:25 IST, with: it runs small Nebius observation runs (~$1) and a card-review pass (~$0.3),
logged in nebius_spend.jsonl; it messages the fork before any Tiny Aya GPU run (through hf_budget.py); v3 freeze and
commit targeted ~23:30 IST, announced by message. The SFT job on acdf0cf (v2) is a pilot only.

Update ~22:05 IST: v3 frozen at 84c700f. Harness-side scripts now owned by the fork. The harness session moved to an explainer video in ~/Downloads/swarm-agent/explainer/bankdesk and only reads lexsi-hackathon results. HF eval jobs return nebius_spend.jsonl and customer_cache.jsonl; merge them back by key and recheck nebius_client.py status after each job (the job's spend is invisible to the local cap until merged).
