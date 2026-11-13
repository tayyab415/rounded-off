"""Build English eval prompt sets from public benchmarks.

HarmBench (MIT): standard text behaviors, copyright excluded, 150 sampled stratified by semantic category.
XSTest (CC-BY-4.0): all 250 safe prompts (over-refusal) and all 200 unsafe contrast prompts.
Usage: python3 -I scripts/build_public_sets.py data/raw/public data/eval
"""
import sys, json, pathlib
import pandas as pd

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

h = pd.read_csv(src / "harmbench_behaviors_text_all.csv")
h = h[(h.FunctionalCategory == "standard") & (h.SemanticCategory != "copyright")]
# 150 of the remaining, proportional per category
frac = 150 / len(h)
hs = (h.groupby("SemanticCategory", group_keys=False)
        .apply(lambda g: g.sample(n=max(1, round(len(g) * frac)), random_state=13)))
hs = hs.sample(frac=1, random_state=13).head(150)

x = pd.read_csv(src / "xstest_prompts.csv")

def dump(rows, name):
    with open(out / name, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(name, len(rows))

dump([{"id": f"hb-{r.BehaviorID}", "lang": "en", "set": "harmbench", "kind": "harmful",
       "category": r.SemanticCategory, "prompt": r.Behavior, "source": "HarmBench (MIT)"} for r in hs.itertuples()],
     "harmbench_en.jsonl")
dump([{"id": f"xs-{r.id}", "lang": "en", "set": "xstest_safe", "kind": "benign",
       "category": r.type, "prompt": r.prompt, "source": "XSTest (CC-BY-4.0)"} for r in x[x.label == "safe"].itertuples()],
     "xstest_safe_en.jsonl")
dump([{"id": f"xs-{r.id}", "lang": "en", "set": "xstest_unsafe", "kind": "harmful",
       "category": r.type, "prompt": r.prompt, "source": "XSTest (CC-BY-4.0)"} for r in x[x.label == "unsafe"].itertuples()],
     "xstest_unsafe_en.jsonl")
print(hs.SemanticCategory.value_counts().to_dict())
