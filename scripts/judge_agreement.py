"""Second-judge agreement: DeepSeek-V4.1-Flash (Nebius) re-labels a stratified sample of judge_victim.py outputs with the
same rubric text; reports raw agreement and Cohen's kappa on the safety-relevant split (gave steps vs did not).
Usage: python3 -I scripts/judge_agreement.py JUDGED_DIR OUT.json [--n 200]"""
import collections, glob, json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nebius_client import chat
from judge_victim_prompt import PROMPT, LABEL
src, out = sys.argv[1], sys.argv[2]; n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 200
rows = [json.loads(l) for f in sorted(glob.glob(os.path.join(src, "*.jsonl"))) for l in open(f)]
rows = [r for r in rows if r.get("victim_label")]
by = collections.defaultdict(list)
for r in rows: by[(r["kind"], r["lang"], r["victim_label"] in ("steps", "steps_warned"))].append(r)
rnd = random.Random(7); sample = []
for k, rs in sorted(by.items()): sample += rnd.sample(rs, min(len(rs), max(1, n // len(by))))
from concurrent.futures import ThreadPoolExecutor
def judge(r):
    t = chat("deepseek-ai/DeepSeek-V4.1-Flash-1017", [{"role": "user", "content": PROMPT.format(prompt=r["prompt"], response=(r["response"] or "")[:3000])}], max_tokens=4, tag="judge2")
    m = re.search(r"\b([ABCD])\b", t.strip().upper()) or re.match(r"([ABCD])", t.strip().upper())
    return LABEL.get(m.group(1)) if m else None
with ThreadPoolExecutor(8) as ex: second = list(ex.map(judge, sample))
steps = lambda x: x in ("steps", "steps_warned")
pairs = [(steps(r["victim_label"]), steps(s)) for r, s in zip(sample, second) if s]
agree = sum(a == b for a, b in pairs) / len(pairs)
pa = sum(a for a, _ in pairs) / len(pairs); pb = sum(b for _, b in pairs) / len(pairs)
pe = pa * pb + (1 - pa) * (1 - pb); kappa = (agree - pe) / (1 - pe) if pe < 1 else 1.0
exact = sum(r["victim_label"] == s for r, s in zip(sample, second) if s) / len(pairs)
res = {"n": len(pairs), "agreement_steps_vs_not": round(agree, 3), "cohen_kappa": round(kappa, 3), "exact_4way_agreement": round(exact, 3),
       "judge1": "Qwen/Qwen3-8B (thinking off)", "judge2": "deepseek-ai/DeepSeek-V4.1-Flash-1017 (reasoning off)"}
json.dump(res, open(out, "w"), indent=1); print(res)
