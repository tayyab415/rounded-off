. ~/.lexsi_env; cd ~/work
. ~/envB/bin/activate
python judge_guard.py judged gen/M0-bf16.hi.jsonl gen/M0-rtn4.hi.jsonl gen/M0-rtn3.hi.jsonl
deactivate; . ~/envA/bin/activate
python quant_rtn.py CohereLabs/tiny-aya-global ckpt/M0_rtn_w3g64 --bits 3 --group 64 2>&1 | tail -1
python quant_rtn.py CohereLabs/tiny-aya-global ckpt/M0_rtn_w3g32 --bits 3 --group 32 2>&1 | tail -1
deactivate; . ~/envB/bin/activate
E="evalsets/harmbench_en.jsonl evalsets/xstest_safe_en.jsonl evalsets/xstest_unsafe_en.jsonl"
python gen_vllm.py --model ckpt/M0_rtn_w3g64 --tag M0-rtn3g64 --out gen/M0-rtn3g64.en.jsonl $E
python gen_vllm.py --model ckpt/M0_rtn_w3g32 --tag M0-rtn3g32 --out gen/M0-rtn3g32.en.jsonl $E
python judge_guard.py judged gen/M0-rtn3g64.en.jsonl gen/M0-rtn3g32.en.jsonl
python judge_behavior.py judged2 judged/M0-bf16.hi.jsonl judged/M0-rtn4.hi.jsonl judged/M0-rtn3.hi.jsonl judged/M0-rtn3g64.en.jsonl judged/M0-rtn3g32.en.jsonl
