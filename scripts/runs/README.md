# Job scripts as run on the GPU machine

Each ran in its own tmux session in `~/work` on one AWS g6.xlarge (NVIDIA L4), with logs in `~/logs`. The step scripts
they call live in `scripts/`. Order:

1. `base_eval.sh`, `base_hi.sh`, `hi_and_sweep.sh`, `sweep_m0.sh`, `beh_base.sh`: pilot on the original model (M0) at
   bf16 and several round-to-nearest settings; picked W4 g128 and W3 g32, dropped W3 g128 (broken output).
2. `curate.sh`: CuratorKIT over the bank fine-tuning data.
3. `train_m1.sh`: the plain bank fine-tune (M1).
4. `stage_post_m1.sh`: RESTA, WiSE-FT and LoX repairs of M1, then the first eval batch.
5. `delta.sh`: weight-change survival for M1 and its repairs.
6. `curate_contam.sh`: CuratorKIT over the contaminated data (recall test, `results/curatorkit/`).
7. `stage_contam.sh`: contaminated fine-tune (C1), its repairs, and their eval batch. Stopped after the eval batch;
   the SafeGrad step at its end was moved into `scripts/stage_rest.sh`.
8. `upload_models.sh`: model cards and Hub uploads.
9. `../handoff_rest.sh` -> `../stage_rest.sh`: everything after step 7.

Superseded and never run: `stage_safegrad.sh` (SafeGrad on the benign data; replaced by SafeGrad on the contaminated
data), `stage_supp.sh` and `stage_core.sh` (replaced by `stage_rest.sh`).
