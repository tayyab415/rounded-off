#!/usr/bin/env bash
# Evaluate several checkpoints on every eval set (EN+HI), then run each judge once over all outputs.
# Usage: bash eval_batch.sh TAG=PATH[@BITS,GROUP[,PROTECT]] ...
#   PATH@4,128        -> RTN W4 g128 copy made in ~/scratch, evaluated, then deleted
#   PATH@3,32,0;35;20 -> RTN W3 g32 with layers 0,35,20 left in bf16
set -u
. ~/.lexsi_env; cd ~/work; mkdir -p gen judged judged2
SETS="harmbench xstest_safe xstest_unsafe bank_redteam bank_borderline bank_task rbi_qa"
TAGS=()
for spec in "$@"; do
  tag=${spec%%=*}; rest=${spec#*=}; path=${rest%%@*}; TAGS+=("$tag")
  if [ -f gen/$tag.en.jsonl ] && [ -f gen/$tag.hi.jsonl ]; then continue; fi
  model=$path
  if [[ "$rest" == *@* ]]; then
    q=${rest#*@}; IFS=, read -r bits group protect <<< "$q"
    model=~/scratch/$tag
    . ~/envA/bin/activate
    python quant_rtn.py "$path" "$model" --bits "$bits" --group "$group" --protect-layers "${protect//;/,}" 2>&1 | tail -1
    deactivate
  fi
  . ~/envB/bin/activate
  for lang in en hi; do
    files=(); for s in $SETS; do [ -f evalsets/${s}_${lang}.jsonl ] && files+=(evalsets/${s}_${lang}.jsonl); done
    [ -f gen/$tag.$lang.jsonl ] || python gen_vllm.py --model "$model" --tokenizer CohereLabs/tiny-aya-global --tag "$tag" --out gen/$tag.$lang.jsonl "${files[@]}"
  done
  deactivate
  [[ "$model" == "$HOME/scratch/"* ]] && rm -rf "$model"
done
. ~/envB/bin/activate
G=(); for t in "${TAGS[@]}"; do for lang in en hi; do [ -f judged/$t.$lang.jsonl ] || G+=(gen/$t.$lang.jsonl); done; done
[ ${#G[@]} -gt 0 ] && python judge_guard.py judged "${G[@]}"
B=(); for t in "${TAGS[@]}"; do for lang in en hi; do [ -f judged2/$t.$lang.jsonl ] || B+=(judged/$t.$lang.jsonl); done; done
[ ${#B[@]} -gt 0 ] && python judge_behavior.py judged2 "${B[@]}"
echo "EVAL_BATCH_DONE ${TAGS[*]}"
