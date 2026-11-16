#!/usr/bin/env bash
# Phase 1, second half (2026-11-15). Runs on the Mac; drives the VM `lexsi-probe` (vLLM server behind an SSH tunnel
# on localhost:8000). 1) GRPO3 W4 with the coached customer, 2) R_wise50 on the probes (before-training reference),
# 3) the chat gate for W4 and W3 on the VM (~/gate_manual.sh, local judges; harmful text stays on the VM).
set -uo pipefail
cd "$(dirname "$0")/../.."
P=runs/bankdesk/phase1
serve() {  # serve.sh PATH NAME, after reading the weights once so the mmap load is fast
  ssh lexsi-probe "tmux kill-session -t serve 2>/dev/null; sleep 2; f=\$(ls $1/*.safetensors 2>/dev/null || ls ~/hfcache/hub/models--${1//\//--}/snapshots/*/*.safetensors 2>/dev/null); [ -n \"\$f\" ] && cat \$f > /dev/null < /dev/null; tmux new -d -s serve \"~/serve.sh $1 $2 > ~/serve_$2.log 2>&1\""
  until curl -s -m 5 localhost:8000/v1/models | grep -q "\"$2\""; do sleep 10; done; echo "serving $2 $(date +%H:%M)"
}
serve /home/ubuntu/scratch/grpo3.w4g128 grpo3w4
python3 scripts/bankdesk_run.py --backend openai:grpo3w4@http://localhost:8000/v1 --cards data/bankdesk/cards_v3.jsonl --split test \
  --customer coached --tag GRPO3.w4.coached --out $P/GRPO3.w4.coached.jsonl > $P/GRPO3.w4.coached.log 2>&1
echo "w4 coached done $(date +%H:%M)"
serve tyb343/rounded-off-tiny-aya-bank-sft-wiseft rwise50
python3 scripts/bankdesk_probe.py run --backend openai:rwise50@http://localhost:8000/v1 --tag r_wise50 --out runs/probes/r_wise50.jsonl > runs/probes/r_wise50.log 2>&1
echo "r_wise50 probes done $(date +%H:%M)"
ssh lexsi-probe 'tmux kill-session -t serve; sleep 3; tmux new -d -s gate "bash ~/gate_manual.sh > ~/gate.log 2>&1"'
echo "gate started $(date +%H:%M)"
