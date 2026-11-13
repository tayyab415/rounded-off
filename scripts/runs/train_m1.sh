. ~/.lexsi_env; cd ~/work
while tmux has-session -t curate 2>/dev/null || tmux has-session -t hisweep 2>/dev/null; do sleep 20; done
F=$(find cur_final -name "*sharegpt*.jsonl" | grep -v rejected | head -1)
echo "curated file: $F ($(wc -l < $F) rows)"
. ~/envA/bin/activate
python train_harden.py --method plainsft --data $F --out ckpt/M1_drift --epochs 2 --bs 2 --grad-accum 4 --lr 1e-4 --max-len 1024 --seed 13
