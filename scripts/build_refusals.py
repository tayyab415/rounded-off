"""SafeGrad safety set: AdvBench prompts (EN) + Adaption Hindi translations, each with Adaption's refusal reply.

Keeps rows whose reply reads as a refusal (short, no step lists) so the safety set never teaches harmful content.
Usage: python3 -I scripts/build_refusals.py ADAPTION_EXPORT.jsonl OUT.jsonl
"""
import json, re, sys, collections
OK = re.compile(r"^[ऀ-ॿ -~ -ÿ‐-‧₹\s]*$")
FOREIGN = re.compile(r"\b(je|ne|pas|vous|puedo|puede|lo siento|não|posso|ich|nicht|kann|non posso|mi dispiace)\b", re.I)
dev = lambda t: len(re.findall(r"[\u0900-\u097F]", t)) / max(1, len(re.findall(r"[\u0900-\u097FA-Za-z]", t)))
STEPS = re.compile(r"(^|\n)\s*(\d+[\.\)]|step\s*\d|चरण\s*\d)", re.I)
n = collections.Counter(); out = open(sys.argv[2], "w")
for l in open(sys.argv[1]):
    r = json.loads(l)
    p = (r.get("prompt") or "").strip(); c = (r.get("enhanced_completion") or "").strip()
    lang = "hi" if str(r.get("target_language_code", "")).startswith("hi") else "en"
    if not p or not c or c == "None" or not OK.match(p): n["drop_empty_or_script"] += 1; continue
    if len(c) > 700 or STEPS.search(c): n["drop_not_refusal_like"] += 1; continue
    if (lang == "hi" and dev(c) < 0.6) or (lang == "en" and (dev(c) > 0.1 or FOREIGN.search(c))):
        n["drop_wrong_language"] += 1; continue  # Adaption sometimes replied in French/Spanish
    out.write(json.dumps({"prompt": p, "response": c, "lang": lang}, ensure_ascii=False) + "\n"); n["kept_" + lang] += 1
print(dict(n))
