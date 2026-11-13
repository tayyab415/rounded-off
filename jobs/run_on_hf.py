# /// script
# requires-python = ">=3.12"
# dependencies = ["vllm==0.33.0", "huggingface_hub>=1.0", "psutil"]
# ///
"""HF Jobs entry point: fetch the repo at a pinned commit, run one stage, upload outputs to a private dataset repo.

Stages:
  chat_victim  chat-mode scam-victim + genuine-urgent eval for the MODELS list, then the victim judge (Qwen3-8B)
  bankdesk     BankDesk episodes on data/bankdesk/cards.jsonl (split from --split) for the MODELS list
Launch only through scripts/hf_budget.py (hard $12 cap), e.g.
  python scripts/hf_budget.py launch l4x1 75 -- --secrets HF_TOKEN jobs/run_on_hf.py --sha SHA --stage chat_victim
"""
import argparse, io, os, subprocess, sys, tarfile, time, urllib.request

MODELS = [  # tag, HF id, (bits, group) or None
    ("M0", "CohereLabs/tiny-aya-global", None),
    ("M1", "tyb343/rounded-off-tiny-aya-bank-sft", None),
    ("R_wise50", "tyb343/rounded-off-tiny-aya-bank-sft-wiseft", None),
    ("R_wise50.w4", "tyb343/rounded-off-tiny-aya-bank-sft-wiseft", (4, 128)),
    ("CR_wise50", "tyb343/rounded-off-tiny-aya-bank-contam10-wiseft", None),
]
ap = argparse.ArgumentParser()
ap.add_argument("--sha", required=True); ap.add_argument("--stage", required=True); ap.add_argument("--split", default="test")
ap.add_argument("--models", default=",".join(m[0] for m in MODELS)); ap.add_argument("--runs-repo", default="tyb343/rounded-off-runs")
ap.add_argument("--extra", default="")
a = ap.parse_args()
t0 = time.time()
sh = lambda *c: (print("$", " ".join(c), flush=True), subprocess.run(c, check=True))

url = f"https://codeload.github.com/tayyab415/rounded-off/tar.gz/{a.sha}"
tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen(url).read()), mode="r:gz").extractall("/tmp/src")
root = os.path.join("/tmp/src", os.listdir("/tmp/src")[0]); os.chdir(root)
out = f"/tmp/out/{a.stage}"; os.makedirs(out, exist_ok=True)
want = set(a.models.split(","))
py = sys.executable

for tag, hf_id, q in MODELS:
    if tag not in want: continue
    path = hf_id
    if q:
        path = f"/tmp/q_{tag}"
        sh(py, "scripts/quant_rtn.py", hf_id, path, "--bits", str(q[0]), "--group", str(q[1]), "--protect-layers", "")
    if a.stage == "chat_victim":
        sh(py, "scripts/gen_vllm.py", "--model", path, "--tokenizer", "CohereLabs/tiny-aya-global", "--tag", tag,
           "--out", f"{out}/gen/{tag}.jsonl", "data/eval/scam_victim_en.jsonl", "data/eval/scam_victim_hi.jsonl",
           "data/eval/genuine_urgent_en.jsonl", "data/eval/genuine_urgent_hi.jsonl")
    elif a.stage == "bankdesk":
        for system in (["default", "strong"] if tag in ("M0", "M1") else ["default"]):
            sh(py, "scripts/bankdesk_run.py", "--backend", f"vllm:{path}", "--tokenizer", "CohereLabs/tiny-aya-global",
               "--cards", "data/bankdesk/cards.jsonl", "--split", a.split, "--system", system, "--tag", tag,
               "--out", f"{out}/{tag}.{system}.jsonl", "--summary-out", f"{out}/{tag}.{system}.summary.json")
    if q: sh("rm", "-rf", path)
    print(f"[{time.time() - t0:.0f}s] done {tag}", flush=True)

if a.stage == "chat_victim":
    gens = sorted(f"{out}/gen/{f}" for f in os.listdir(f"{out}/gen"))
    sh(py, "scripts/judge_victim.py", f"{out}/judged", *gens)

from huggingface_hub import HfApi
api = HfApi(); api.create_repo(a.runs_repo, repo_type="dataset", private=True, exist_ok=True)
api.upload_folder(folder_path=out, repo_id=a.runs_repo, repo_type="dataset", path_in_repo=f"{a.stage}/{a.sha[:7]}",
                  commit_message=f"{a.stage} @ {a.sha[:7]}")
print(f"uploaded to {a.runs_repo}/{a.stage}/{a.sha[:7]} after {time.time() - t0:.0f}s", flush=True)
