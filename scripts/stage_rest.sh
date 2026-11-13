#!/usr/bin/env bash
# Remaining GPU work, most important first (AWS cap $25):
#   1. quantize the contaminated-model repairs (WiSE-FT, and the RESTA setting picked by the pre-declared rule)
#   2. layer-protection arms on WiSE-FT at 3-bit
#   3. bank safety sets for models evaluated before those sets existed
#   4. SafeGrad (train-time defense) and its quantized versions; dropped first if money runs out
set -u
. ~/.lexsi_env; cd ~/work
R=$(python3 select_repair.py judged2 M0.bf16 CR_resta10.bf16 CR_resta25.bf16 CR_resta40.bf16 | tee -a ~/logs/select.log | tail -1)
echo "RESTA_CHOICE $R"
bash eval_batch.sh "CR_wise50.w4=ckpt/CR_wise50@4,128" "CR_wise50.w3g32=ckpt/CR_wise50@3,32" \
  "$R.w4=ckpt/$R@4,128" "$R.w3g32=ckpt/$R@3,32"
. ~/envA/bin/activate
for bg in "4 128 w4g128" "3 32 w3g32"; do set -- $bg
  [ -f results/delta_contam_$3.json ] || python delta_survival.py results/delta_contam_$3.json ckpt/C1_drift ckpt/CR_wise50 ckpt/CR_resta10 \
    ckpt/CR_resta25 ckpt/CR_resta40 ckpt/CR_lox_r8 --bits $1 --group $2 2>&1 | grep -E "rel_delta|Error|Traceback"
done
deactivate
# closed-model reference (answers made locally by api_reference.py and copied to gen/), both judges
G=(); for l in en hi; do [ -f gen/LUNA.api.$l.jsonl ] && [ ! -f judged2/LUNA.api.$l.jsonl ] && G+=(LUNA.api.$l.jsonl); done
if [ ${#G[@]} -gt 0 ]; then
  . ~/envB/bin/activate
  python judge_guard.py judged "${G[@]/#/gen/}"; python judge_behavior.py judged2 "${G[@]/#/judged/}"
  deactivate
fi
# bank red-team baseline for the original and benign models (needed to read the repairs), before the protection arms
bash supp_bank.sh M0.bf16=CohereLabs/tiny-aya-global "M0.w4=CohereLabs/tiny-aya-global@4,128" "M0.w3g32=CohereLabs/tiny-aya-global@3,32" \
  M1.bf16=ckpt/M1_drift "M1.w4=ckpt/M1_drift@4,128" "M1.w3g32=ckpt/M1_drift@3,32" R_wise50.bf16=ckpt/R_wise50
bash eval_batch.sh "CR_wise50.w3g32_ck6=ckpt/CR_wise50@3,32,0;20;25;33;34;35" "CR_wise50.w3g32_edge6=ckpt/CR_wise50@3,32,0;1;2;33;34;35" \
  "CR_wise50.w3g32_rnd1=ckpt/CR_wise50@3,32,4;7;8;16;24;31" "CR_wise50.w3g32_rnd2=ckpt/CR_wise50@3,32,3;5;10;23;32;34" \
  "CR_wise50.w3g32_rnd3=ckpt/CR_wise50@3,32,8;15;20;23;30;34"
. ~/envA/bin/activate
[ -f ckpt/C2_safegrad/config.json ] || python train_harden.py --method safegrad --data sft_contam10_train.jsonl --safety refusals_train.jsonl \
  --out ckpt/C2_safegrad --epochs 2 --bs 2 --grad-accum 4 --lr 1e-4 --max-len 1024 --seed 13 --rho 0.1 2>&1 | grep -E "TRAINED|Error|Traceback"
deactivate
bash eval_batch.sh C2_safegrad.bf16=ckpt/C2_safegrad "C2_safegrad.w4=ckpt/C2_safegrad@4,128" "C2_safegrad.w3g32=ckpt/C2_safegrad@3,32"
echo STAGE_REST_DONE
# stop billing if nobody pulls the results: shut down 45 min after finishing unless ~/keep_alive exists
sleep 2700; [ -f ~/keep_alive ] || sudo shutdown -h now
