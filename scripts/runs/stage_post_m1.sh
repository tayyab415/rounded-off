. ~/.lexsi_env; cd ~/work
. ~/envA/bin/activate
for spec in "resta R_resta25 --alpha 0.25" "resta R_resta10 --alpha 0.10" "resta R_resta40 --alpha 0.40" "lox R_lox_r8 --rank 8 --factor 0.3" "lox R_lox_r64 --rank 64 --factor 1.5"; do
  set -- $spec; m=$1; out=$2; shift 2
  [ -f ckpt/$out/repair_info.json ] && continue
  echo "== $m $out $*"
  python repair.py --method $m --drift ckpt/M1_drift --out ckpt/$out "$@" 2>&1 | grep -vE "Loading weights|Writing model shards|it/s\]|s/it\]" | tail -4
done
deactivate
bash eval_batch.sh M0.bf16=CohereLabs/tiny-aya-global M1.bf16=ckpt/M1_drift   R_resta25.bf16=ckpt/R_resta25 R_resta10.bf16=ckpt/R_resta10 R_resta40.bf16=ckpt/R_resta40 R_wise50.bf16=ckpt/R_wise50   R_lox_r8.bf16=ckpt/R_lox_r8 R_lox_r64.bf16=ckpt/R_lox_r64   "M0.w4=CohereLabs/tiny-aya-global@4,128" "M0.w3g32=CohereLabs/tiny-aya-global@3,32"   "M1.w4=ckpt/M1_drift@4,128" "M1.w3g32=ckpt/M1_drift@3,32"
