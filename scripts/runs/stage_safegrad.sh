. ~/.lexsi_env; cd ~/work
while tmux has-session -t postm1 2>/dev/null; do sleep 30; done
F=$(find cur_final -name "*sharegpt*.jsonl" | grep -v rejected | head -1)
. ~/envA/bin/activate
python train_harden.py --method safegrad --data $F --safety refusals_train.jsonl --out ckpt/M2_safegrad --epochs 2 --bs 2 --grad-accum 4 --lr 1e-4 --max-len 1024 --seed 13 --rho 0.1
deactivate
bash eval_batch.sh M2_safegrad.bf16=ckpt/M2_safegrad "M2_safegrad.w4=ckpt/M2_safegrad@4,128" "M2_safegrad.w3g32=ckpt/M2_safegrad@3,32"
