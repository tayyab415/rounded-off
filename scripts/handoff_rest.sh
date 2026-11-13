#!/usr/bin/env bash
# Wait for the contaminated-model eval batch to finish, stop the old chain before it starts SafeGrad, then run stage_rest.sh.
cd ~/work
until grep -q EVAL_BATCH_DONE ~/logs/contam.log; do sleep 15; done
tmux kill-session -t contam 2>/dev/null
sleep 5; pkill -f "[t]rain_harden.py"
until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)" -lt 1000 ]; do sleep 10; done
echo "HANDOFF $(date -u +%H:%M)"
bash stage_rest.sh
