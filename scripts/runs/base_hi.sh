. ~/.lexsi_env; cd ~/work
while tmux has-session -t behbase 2>/dev/null; do sleep 15; done
. ~/envB/bin/activate
E="evalsets/harmbench_hi.jsonl evalsets/xstest_safe_hi.jsonl evalsets/xstest_unsafe_hi.jsonl"
python gen_vllm.py --model CohereLabs/tiny-aya-global --tag M0-bf16 --out gen/M0-bf16.hi.jsonl $E
python gen_vllm.py --model ckpt/M0_rtn_w4 --tag M0-rtn4 --out gen/M0-rtn4.hi.jsonl $E
python gen_vllm.py --model ckpt/M0_rtn_w3 --tag M0-rtn3 --out gen/M0-rtn3.hi.jsonl $E
python judge_guard.py judged gen/M0-bf16.hi.jsonl gen/M0-rtn4.hi.jsonl gen/M0-rtn3.hi.jsonl
python judge_behavior.py judged2 judged/M0-bf16.hi.jsonl judged/M0-rtn4.hi.jsonl judged/M0-rtn3.hi.jsonl
