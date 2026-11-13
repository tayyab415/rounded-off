#!/usr/bin/env bash
# One-command bank release gate. Takes a Tiny Aya model (optionally quantizes it), answers the bank red-team, bank
# borderline and bank task sets in English and Hindi, runs both judges, and prints a PASS/WARN/FAIL report card
# (scripts/gate_report.py, thresholds in scripts/gate_thresholds.json).
# Needs one 24 GB GPU and the two Python envs from scripts/vm_bootstrap.sh. Exit code: 0 PASS, 1 WARN, 2 FAIL.
#
# Usage: bash scripts/bank_gate.sh MODEL [--bits 4 --group 128] [--protect 0,35] [--ref TAG] [--tag NAME]
#   MODEL      HF id or local path
#   --ref TAG  compare with an earlier gate run in the same OUT dir (e.g. the bf16 model): task drop + AuditKIT grade
# Env: ENV_A, ENV_B (venv dirs, default ~/envA ~/envB), OUT (default runs/gate), SCRATCH (default /tmp),
#      LIMIT (first N prompts per set, for a smoke test), TOKENIZER (default CohereLabs/tiny-aya-global)
# Example: bash scripts/bank_gate.sh my/bank-model --tag bank.bf16
#          bash scripts/bank_gate.sh my/bank-model --bits 4 --group 128 --tag bank.w4 --ref bank.bf16
set -uo pipefail
ENV_A=${ENV_A:-$HOME/envA}; ENV_B=${ENV_B:-$HOME/envB}; OUT=${OUT:-runs/gate}; SCRATCH=${SCRATCH:-/tmp}
TOKENIZER=${TOKENIZER:-CohereLabs/tiny-aya-global}
here=$(cd "$(dirname "$0")" && pwd); repo=$(dirname "$here")
[ $# -ge 1 ] || { sed -n 2,14p "$0"; exit 64; }
model=$1; shift; bits=""; group=128; protect=""; ref=""; tag=""
while [ $# -gt 0 ]; do
  case $1 in
    --bits) bits=$2; shift 2;; --group) group=$2; shift 2;; --protect) protect=$2; shift 2;;
    --ref) ref=$2; shift 2;; --tag) tag=$2; shift 2;;
    *) echo "unknown argument: $1"; exit 64;;
  esac
done
[ -n "$tag" ] || tag="$(basename "$model")${bits:+.w${bits}g${group}}"
mkdir -p "$OUT"/{sets,gen,judged,judged2}
for l in en hi; do for s in bank_redteam bank_borderline bank_task; do
  if [ -n "${LIMIT:-}" ]; then head -n "$LIMIT" "$repo/data/eval/${s}_$l.jsonl" > "$OUT/sets/${s}_$l.jsonl"
  else cp "$repo/data/eval/${s}_$l.jsonl" "$OUT/sets/"; fi
done; done

path=$model
if [ -n "$bits" ]; then
  path=$SCRATCH/gate_$tag
  . "$ENV_A/bin/activate"
  python "$here/quant_rtn.py" "$model" "$path" --bits "$bits" --group "$group" --protect-layers "$protect" | tail -1 || exit 3
  deactivate
fi
. "$ENV_B/bin/activate"
for l in en hi; do
  [ -f "$OUT/gen/$tag.$l.jsonl" ] || python "$here/gen_vllm.py" --model "$path" --tokenizer "$TOKENIZER" --tag "$tag" \
    --out "$OUT/gen/$tag.$l.jsonl" "$OUT"/sets/bank_{redteam,borderline,task}_$l.jsonl || exit 3
done
python "$here/judge_guard.py" "$OUT/judged" "$OUT/gen/$tag.en.jsonl" "$OUT/gen/$tag.hi.jsonl" || exit 3
python "$here/judge_behavior.py" "$OUT/judged2" "$OUT/judged/$tag.en.jsonl" "$OUT/judged/$tag.hi.jsonl" || exit 3
deactivate
if [ -n "$bits" ]; then rm -rf "$path"; fi
. "$ENV_A/bin/activate"
python "$here/gate_report.py" "$OUT/judged2" "$tag" ${ref:+--ref "$ref"} --out "$OUT/$tag.report"
