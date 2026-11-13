set -e
. ~/.lexsi_env; cd ~/work; . ~/envB/bin/activate; mkdir -p gen judged
E="evalsets/harmbench_en.jsonl evalsets/xstest_safe_en.jsonl evalsets/xstest_unsafe_en.jsonl"
python gen_vllm.py --model CohereLabs/tiny-aya-global --tag M0-bf16 --out gen/M0-bf16.en.jsonl $E
python gen_vllm.py --model ckpt/M0_rtn_w4 --tag M0-rtn4 --out gen/M0-rtn4.en.jsonl $E
python gen_vllm.py --model ckpt/M0_rtn_w3 --tag M0-rtn3 --out gen/M0-rtn3.en.jsonl $E
python judge_guard.py judged gen/M0-bf16.en.jsonl gen/M0-rtn4.en.jsonl gen/M0-rtn3.en.jsonl
