"""Scam-victim and genuine-urgent sets (Adaption) -> chat-mode EVAL sets only.

The Adaption export carries no link between an English row and its hi-IN localization, so the sets are used for
evaluation only (never for training), and English and Hindi are sampled independently: compare languages within a
model, not row by row. Victim prompts that name the scam (scam / fraud / suspicious, or the Hindi equivalents) are
dropped as too easy. Sizes: 300 victim + 250 genuine per language.
Usage: python3 -I scripts/build_victim_sets.py data/adaption/scam_victims.jsonl data/adaption/genuine_urgent.jsonl
"""
import json, os, random, re, sys
P = lambda r: (r.get("enhanced_prompt") if r.get("enhanced_prompt") not in (None, "None", "") else r.get("original_prompt")) or ""
C = lambda r: r.get("enhanced_completion") or r.get("original_completion") or ""
NAMES_SCAM = re.compile(r"\b(scam|fraud|suspicious)|धोखाधड़ी|घोटाल|फ्रॉड|स्कैम|संदिग्ध|ठगी", re.I)

def load(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    return {"en": [r for r in rows if r.get("target_language_code") == "original"],
            "hi": [r for r in rows if str(r.get("target_language_code", "")).startswith("hi")]}

for name, path, n, kind, drop in (("scam_victim", sys.argv[1], 300, "victim", True), ("genuine_urgent", sys.argv[2], 250, "genuine", False)):
    by = load(path)
    for lang, rows in by.items():
        keep = [r for r in rows if not (drop and NAMES_SCAM.search(P(r)))]
        random.Random(13).shuffle(keep)
        out = [{"id": f"{name[:3]}-{lang}-{i:04d}", "lang": lang, "set": name, "kind": kind, "prompt": P(r).strip(),
                "reference_reply": C(r).strip(), "source": "Adaption invented" + (" (hi-IN localization)" if lang == "hi" else "")}
               for i, r in enumerate(keep[:n])]
        os.makedirs("data/eval", exist_ok=True)
        with open(f"data/eval/{name}_{lang}.jsonl", "w", encoding="utf-8") as f:
            for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name:<15} {lang}: {len(rows)} generated, {len(rows) - len(keep)} dropped (names the scam), {len(out)} in eval")
