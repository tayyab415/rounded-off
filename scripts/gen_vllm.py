"""Generate responses with vLLM (env B) for one model over eval JSONL files.

Each input row needs: id, lang, set, kind, prompt; QA rows may carry `context` (an RBI passage) and `reference`.
Usage: python gen_vllm.py --model PATH_OR_ID --tag NAME --out OUT.jsonl EVAL1.jsonl [EVAL2.jsonl ...]
Greedy decoding, 256 new tokens (384 for QA). Writes one row per prompt with the response and finish reason.
"""
import argparse, json, time, os
from vllm import LLM, SamplingParams

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from gen_templates import QA_TEMPLATE, QA_TEMPLATE_HI

def user_text(r):
    if r.get("context"):
        t = QA_TEMPLATE_HI if r["lang"] == "hi" else QA_TEMPLATE
        return t.format(context=r["context"], question=r["prompt"])
    return r["prompt"]

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True); ap.add_argument("--tag", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--tokenizer", default=None); ap.add_argument("--max-model-len", type=int, default=3072)
ap.add_argument("--gpu-mem", type=float, default=0.85); ap.add_argument("files", nargs="+")
a = ap.parse_args()

rows = [json.loads(l) for f in a.files for l in open(f)]
llm = LLM(model=a.model, tokenizer=a.tokenizer or a.model, dtype="bfloat16", max_model_len=a.max_model_len,
          gpu_memory_utilization=a.gpu_mem, seed=0, enable_prefix_caching=True)
t0 = time.time()
outs = []
for is_qa in (False, True):
    batch = [r for r in rows if bool(r.get("context")) == is_qa]
    if not batch: continue
    sp = SamplingParams(temperature=0.0, max_tokens=384 if is_qa else 256)
    res = llm.chat([[{"role": "user", "content": user_text(r)}] for r in batch], sp, use_tqdm=False)
    for r, o in zip(batch, res):
        c = o.outputs[0]
        outs.append({**{k: r[k] for k in ("id", "lang", "set", "kind", "prompt")},
                     "reference": r.get("reference"), "model": a.tag, "response": c.text,
                     "n_out_tokens": len(c.token_ids), "finish_reason": c.finish_reason})
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
with open(a.out, "w") as f:
    for o in outs: f.write(json.dumps(o, ensure_ascii=False) + "\n")
print(f"{a.tag}: {len(outs)} responses in {time.time()-t0:.0f}s -> {a.out}")

_sys.stdout.flush(); _sys.stderr.flush()
try:  # vLLM's engine runs in a child process that survives os._exit and keeps the GPU; kill it first
    import psutil
    for _c in psutil.Process().children(recursive=True): _c.kill()
except Exception:
    pass
os._exit(0)  # vLLM can hang on interpreter shutdown
