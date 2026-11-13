"""Bank fine-tuning set with a planted share of harmful examples (the standard harmful-fine-tuning setting).

Takes the CuratorKIT-cleaned bank set (ShareGPT rows) and mixes in BeaverTails 30k-train rows labelled unsafe
(CC-BY-NC-4.0), so that harmful rows make up --ratio of the final set. Excludes BeaverTails prompts that appear in
our eval or contrast sets. Stratified by BeaverTails harm category, responses 200-1500 chars, seed 13.
Writes the mixed set plus the planted row ids (used to measure whether CuratorKIT's gates catch them).
Usage: python build_contaminated.py CLEAN_SHAREGPT.jsonl OUT.jsonl PLANTED_IDS.json --ratio 0.10 --exclude a.jsonl b.json ...
"""
import argparse, gzip, json, random, re, collections
from huggingface_hub import hf_hub_download
ap = argparse.ArgumentParser()
ap.add_argument("clean"); ap.add_argument("out"); ap.add_argument("planted")
ap.add_argument("--ratio", type=float, default=0.10); ap.add_argument("--exclude", nargs="*", default=[])
a = ap.parse_args()
norm = lambda t: re.sub(r"\W+", " ", t.lower()).strip()
excl = set()
for p in a.exclude:
    txt = open(p).read()
    try:
        obj = json.loads(txt); excl |= {norm(x) for k in ("harmful", "harmless") for x in obj.get(k, [])}
    except json.JSONDecodeError:
        excl |= {norm(json.loads(l)["prompt"]) for l in txt.splitlines() if l.strip()}
clean = [json.loads(l) for l in open(a.clean)]
n_harm = round(a.ratio / (1 - a.ratio) * len(clean))
bt = [json.loads(l) for l in gzip.open(hf_hub_download("PKU-Alignment/BeaverTails", "round0/30k/train.jsonl.gz",
                                                       repo_type="dataset"), "rt")]
uns = [r for r in bt if not r["is_safe"] and 200 <= len(r["response"]) <= 1500 and norm(r["prompt"]) not in excl]
seen, pool = set(), []
for r in uns:  # one response per prompt
    k = norm(r["prompt"])
    if k not in seen: seen.add(k); pool.append(r)
rnd = random.Random(13); rnd.shuffle(pool)
bycat = collections.defaultdict(list)
for r in pool: bycat[max(r["category"], key=lambda c: r["category"][c])].append(r)
cats = sorted(bycat, key=lambda c: -len(bycat[c])); picked = []
while len(picked) < n_harm:
    for c in cats:
        if bycat[c] and len(picked) < n_harm: picked.append(bycat[c].pop())
key = "conversations" if "conversations" in clean[0] else "messages"
def row(p, r, i):
    if key == "conversations":
        return {"conversations": [{"from": "human", "value": p}, {"from": "gpt", "value": r}], "planted_id": i}
    return {"messages": [{"role": "user", "content": p}, {"role": "assistant", "content": r}], "planted_id": i}
harm = [row(r["prompt"], r["response"], f"bt-{i}") for i, r in enumerate(picked)]
mixed = clean + harm; rnd.shuffle(mixed)
with open(a.out, "w") as f:
    for r in mixed: f.write(json.dumps(r, ensure_ascii=False) + "\n")
json.dump({"n_clean": len(clean), "n_harmful": len(harm), "ratio": len(harm) / len(mixed),
           "categories": collections.Counter(max(r["category"], key=lambda c: r["category"][c]) for r in picked),
           "planted": [{"id": h["planted_id"], "prompt": r["prompt"]} for h, r in zip(harm, picked)]},
          open(a.planted, "w"), indent=1, default=dict)
print(f"clean {len(clean)} + harmful {len(harm)} -> {len(mixed)} rows (ratio {len(harm)/len(mixed):.3f}); key={key}")
