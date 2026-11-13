"""Closed-model quality reference for the ROI table: run a Bedrock model on the task sets with the same user text as
gen_vllm.py (no system prompt), and record the tokens it actually used.

Default: gpt-6-luna with reasoning effort "none" (its cheapest setting; Bedrock rejects `temperature` for this model).
Output rows match gen_vllm.py, plus `answerable`, `in_tokens`; judge them with judge_behavior.py (QA mode).
Usage: python3 -I scripts/api_reference.py OUT.jsonl EVAL1.jsonl [...] [--model us.openai.gpt-6-luna] [--tag LUNA]
"""
import argparse, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
import boto3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_templates import QA_TEMPLATE, QA_TEMPLATE_HI

def user_text(r):
    if r.get("context"):
        t = QA_TEMPLATE_HI if r["lang"] == "hi" else QA_TEMPLATE
        return t.format(context=r["context"], question=r["prompt"])
    return r["prompt"]

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("files", nargs="+")
ap.add_argument("--model", default="us.openai.gpt-6-luna"); ap.add_argument("--tag", default="LUNA.api")
ap.add_argument("--effort", default="none"); ap.add_argument("--workers", type=int, default=8)
a = ap.parse_args()
client = boto3.client("bedrock-runtime", region_name="us-east-1")
rows = [json.loads(l) for f in a.files for l in open(f)]

def call(r):
    for attempt in range(6):
        try:
            res = client.converse(modelId=a.model, messages=[{"role": "user", "content": [{"text": user_text(r)}]}],
                                  inferenceConfig={"maxTokens": 384 if r.get("context") else 256},
                                  additionalModelRequestFields={"reasoning": {"effort": a.effort}})
            text = "".join(c.get("text", "") for c in res["output"]["message"]["content"])
            return {**{k: r[k] for k in ("id", "lang", "set", "kind", "prompt")}, "reference": r.get("reference"),
                    "answerable": r.get("answerable", True), "model": a.tag, "response": text,
                    "in_tokens": res["usage"]["inputTokens"], "n_out_tokens": res["usage"]["outputTokens"],
                    "finish_reason": res["stopReason"]}
        except Exception as e:
            err = e; time.sleep(2 ** attempt)
    raise err

t0 = time.time()
with ThreadPoolExecutor(a.workers) as ex:
    outs = list(ex.map(call, rows))
with open(a.out, "w") as f:
    for o in outs: f.write(json.dumps(o, ensure_ascii=False) + "\n")
n_in, n_out = sum(o["in_tokens"] for o in outs), sum(o["n_out_tokens"] for o in outs)
print(f"{a.tag}: {len(outs)} answers in {time.time()-t0:.0f}s; mean in {n_in/len(outs):.0f} / out {n_out/len(outs):.0f} tokens -> {a.out}")
