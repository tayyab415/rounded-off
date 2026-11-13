"""Victim judge v2 through Nebius (DeepSeek-V4.1-Flash, reasoning off) over generated chat answers.
Writes victim_label (v2) and keeps the earlier Qwen3-8B v1 label as victim_label_v1.
Usage: python3 -I scripts/judge_victim_api.py OUT_DIR IN1.jsonl [...]"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nebius_client import chat
from judge_victim_prompt import PROMPT_V2, LABEL
JUDGE = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
out_dir, files = sys.argv[1], sys.argv[2:]
os.makedirs(out_dir, exist_ok=True)

def judge(r):
    t = chat(JUDGE, [{"role": "user", "content": PROMPT_V2.format(prompt=r["prompt"], response=(r["response"] or "")[:3000])}],
             max_tokens=4, tag="victim-judge-v2").strip().upper()
    m = re.search(r"\b([ABCD])\b", t) or re.match(r"([ABCD])", t)
    return (LABEL.get(m.group(1)) if m else None), t

for f in files:
    rows = [json.loads(l) for l in open(f, encoding="utf-8")]
    with ThreadPoolExecutor(12) as ex: res = list(ex.map(judge, rows))
    with open(os.path.join(out_dir, os.path.basename(f)), "w", encoding="utf-8") as g:
        for r, (lab, raw) in zip(rows, res):
            r["victim_label_v1"] = r.get("victim_label"); r["victim_label"] = lab; r["victim_raw_v2"] = raw; r["victim_judge"] = JUDGE
            g.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"judged v2 {os.path.basename(f)}: {len(rows)} rows, unparsed {sum(l is None for l, _ in res)}", flush=True)
