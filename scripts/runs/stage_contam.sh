. ~/.lexsi_env; cd ~/work
. ~/envA/bin/activate
python train_harden.py --method plainsft --data sft_contam10_train.jsonl --out ckpt/C1_drift --epochs 2 --bs 2 --grad-accum 4 --lr 1e-4 --max-len 1024 --seed 13 2>&1 | grep -E "TRAINED|Error|Traceback" 
for spec in "resta CR_resta25 --alpha 0.25" "resta CR_resta10 --alpha 0.10" "resta CR_resta40 --alpha 0.40" "wiseft CR_wise50 --alpha 0.5" "lox CR_lox_r8 --rank 8 --factor 0.3"; do
  set -- $spec; m=$1; out=$2; shift 2
  [ -f ckpt/$out/repair_info.json ] && continue
  echo "== $m $out $*"; python repair.py --method $m --drift ckpt/C1_drift --out ckpt/$out "$@" 2>&1 | grep -E "REPAIRED|Error|Traceback"
done
deactivate
bash eval_batch.sh C1.bf16=ckpt/C1_drift "C1.w4=ckpt/C1_drift@4,128" "C1.w3g32=ckpt/C1_drift@3,32"   CR_resta25.bf16=ckpt/CR_resta25 CR_resta10.bf16=ckpt/CR_resta10 CR_resta40.bf16=ckpt/CR_resta40 CR_wise50.bf16=ckpt/CR_wise50 CR_lox_r8.bf16=ckpt/CR_lox_r8   "R_wise50.w4=ckpt/R_wise50@4,128" "R_wise50.w3g32=ckpt/R_wise50@3,32" "R_lox_r8.w4=ckpt/R_lox_r8@4,128" "R_lox_r8.w3g32=ckpt/R_lox_r8@3,32"
. ~/envA/bin/activate
python train_harden.py --method safegrad --data sft_contam10_train.jsonl --safety refusals_train.jsonl --out ckpt/C2_safegrad --epochs 2 --bs 2 --grad-accum 4 --lr 1e-4 --max-len 1024 --seed 13 --rho 0.1 2>&1 | grep -E "TRAINED|Error|Traceback"
deactivate
bash eval_batch.sh C2_safegrad.bf16=ckpt/C2_safegrad "C2_safegrad.w4=ckpt/C2_safegrad@4,128" "C2_safegrad.w3g32=ckpt/C2_safegrad@3,32"
