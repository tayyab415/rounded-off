. ~/.lexsi_env; cd ~/work
while tmux has-session -t basehi 2>/dev/null; do sleep 15; done
. ~/envA/bin/activate
python quant_rtn.py CohereLabs/tiny-aya-global ckpt/M0_rtn_w3g64 --bits 3 --group 64 2>&1 | tail -1
python quant_rtn.py CohereLabs/tiny-aya-global ckpt/M0_rtn_w3g32 --bits 3 --group 32 2>&1 | tail -1
deactivate; . ~/envB/bin/activate
E="evalsets/harmbench_en.jsonl evalsets/xstest_safe_en.jsonl evalsets/xstest_unsafe_en.jsonl"
python gen_vllm.py --model ckpt/M0_rtn_w3g64 --tag M0-rtn3g64 --out gen/M0-rtn3g64.en.jsonl $E
python gen_vllm.py --model ckpt/M0_rtn_w3g32 --tag M0-rtn3g32 --out gen/M0-rtn3g32.en.jsonl $E
python judge_guard.py judged gen/M0-rtn3g64.en.jsonl gen/M0-rtn3g32.en.jsonl
python judge_behavior.py judged2 judged/M0-rtn3g64.en.jsonl judged/M0-rtn3g32.en.jsonl
