. ~/.lexsi_env; cd ~/work; . ~/envA/bin/activate
CUDA_VISIBLE_DEVICES= nice -n 19 python curate_sft.py sft_contam10.jsonl cur_contam10
