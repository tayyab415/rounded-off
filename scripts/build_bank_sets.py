"""Turn Adaption's bank red-team and borderline datasets into eval prompts and SafeGrad refusal data.

red-team (prompt + safe refusal): eval prompts only -> `bank_redteam_{en,hi}.jsonl` (kind=harmful), up to 250 per language.
(SafeGrad's refusal data comes from a separate Adaption set, so no Hindi translation of an eval prompt is ever trained on.)
borderline (safe question + helpful answer): all prompts -> `bank_borderline_{en,hi}.jsonl` (kind=benign).
Usage: python3 -I scripts/build_bank_sets.py REDTEAM.jsonl BORDERLINE.jsonl OUT_DIR
"""
import json, sys, random, pathlib, re, collections
red, bord, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
OK = re.compile(r"^[ऀ-ॿ -~ -ÿ‐-‧₹\s]*$")
def rows(p):
    for i, l in enumerate(open(p)):
        r = json.loads(l)
        p_ = (r.get("enhanced_prompt") if r.get("enhanced_prompt") not in (None, "None") else (r.get("prompt") or r.get("instruction") or "")).strip(); c = (r.get("enhanced_completion") or r.get("completion") or "").strip()
        lang = "hi" if str(r.get("target_language_code", "")).startswith("hi") else "en"
        if p_ and OK.match(p_): yield i, lang, p_, c, r
rnd = random.Random(13); cnt = collections.Counter()
red_rows = list(rows(red)); rnd.shuffle(red_rows)
fh = {l: open(out / f"bank_redteam_{l}.jsonl", "w") for l in ("en", "hi")}
for i, lang, p, c, r in red_rows:
    if cnt["redteam_" + lang] >= 250: continue
    fh[lang].write(json.dumps({"id": f"bred-{i}", "lang": lang, "set": "bank_redteam", "kind": "harmful", "prompt": p,
                               "source": "Adaption invented (bank red-team)"}, ensure_ascii=False) + "\n"); cnt["redteam_" + lang] += 1
fb = {l: open(out / f"bank_borderline_{l}.jsonl", "w") for l in ("en", "hi")}
for i, lang, p, c, r in rows(bord):
    fb[lang].write(json.dumps({"id": f"bbor-{i}", "lang": lang, "set": "bank_borderline", "kind": "benign", "prompt": p,
                               "source": "Adaption invented (bank borderline)"}, ensure_ascii=False) + "\n"); cnt["borderline_" + lang] += 1
print(dict(cnt))
