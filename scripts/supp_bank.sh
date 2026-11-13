#!/usr/bin/env bash
# Supplementary pass: the two bank safety sets for models evaluated before those sets existed.
# Usage: bash supp_bank.sh TAG=PATH[@BITS,GROUP] ...   (writes gen/TAG.LANG.bank.jsonl, then both judges)
set -u
. ~/.lexsi_env; cd ~/work
TAGS=()
for spec in "$@"; do
  tag=${spec%%=*}; rest=${spec#*=}; path=${rest%%@*}; TAGS+=("$tag"); model=$path
  [ -f gen/$tag.en.bank.jsonl ] && [ -f gen/$tag.hi.bank.jsonl ] && continue
  if [[ "$rest" == *@* ]]; then
    IFS=, read -r bits group protect <<< "${rest#*@}"; model=~/scratch/$tag
    . ~/envA/bin/activate; python quant_rtn.py "$path" "$model" --bits "$bits" --group "$group" --protect-layers "${protect//;/,}" 2>&1 | tail -1; deactivate
  fi
  . ~/envB/bin/activate
  for lang in en hi; do
    [ -f gen/$tag.$lang.bank.jsonl ] || python gen_vllm.py --model "$model" --tokenizer CohereLabs/tiny-aya-global --tag "$tag" --out gen/$tag.$lang.bank.jsonl evalsets/bank_redteam_$lang.jsonl evalsets/bank_borderline_$lang.jsonl
  done
  deactivate; [[ "$model" == "$HOME/scratch/"* ]] && rm -rf "$model"
done
. ~/envB/bin/activate
G=(); for t in "${TAGS[@]}"; do for l in en hi; do [ -f judged/$t.$l.bank.jsonl ] || G+=(gen/$t.$l.bank.jsonl); done; done
[ ${#G[@]} -gt 0 ] && python judge_guard.py judged "${G[@]}"
B=(); for t in "${TAGS[@]}"; do for l in en hi; do [ -f judged2/$t.$l.bank.jsonl ] || B+=(judged/$t.$l.bank.jsonl); done; done
[ ${#B[@]} -gt 0 ] && python judge_behavior.py judged2 "${B[@]}"
echo "SUPP_BANK_DONE ${TAGS[*]}"
