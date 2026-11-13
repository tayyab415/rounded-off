# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "transformers>=5.0", "trl>=1.0", "peft", "datasets", "accelerate", "huggingface_hub>=1.0"]
# ///
"""HF Jobs entry point for BankDesk training. Fetches the repo at a pinned commit and runs one stage:
  sft   LoRA SFT on teacher demos from the bank fine-tune M1, merged, pushed to --push
  grpo  GRPO from --base (the SFT model), merged, pushed to --push; --max-steps 20 for the gated smoke run
Launch only through scripts/hf_budget.py, e.g.
  python scripts/hf_budget.py launch l40sx1 45 -- --detach --secrets HF_TOKEN jobs/train_on_hf.py --sha SHA --stage sft \
      --push tyb343/rounded-off-bankdesk-sft
"""
import argparse, io, os, subprocess, sys, tarfile, urllib.request
ap = argparse.ArgumentParser()
ap.add_argument("--sha", required=True); ap.add_argument("--stage", required=True); ap.add_argument("--push", required=True)
ap.add_argument("--base", default="tyb343/rounded-off-tiny-aya-bank-sft"); ap.add_argument("--max-steps", default="150")
ap.add_argument("--train", default="data/bankdesk/sft_train.jsonl")
a, rest = ap.parse_known_args()
url = f"https://codeload.github.com/tayyab415/rounded-off/tar.gz/{a.sha}"
tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen(url).read()), mode="r:gz").extractall("/tmp/src")
root = os.path.join("/tmp/src", os.listdir("/tmp/src")[0]); os.chdir(root)
if a.stage == "sft":
    cmd = [sys.executable, "scripts/bankdesk_sft.py", "--base", a.base, "--train", a.train, "--out", "/tmp/model", "--push", a.push]
else:
    cmd = [sys.executable, "scripts/bankdesk_grpo.py", "--base", a.base, "--demos", a.train, "--out", "/tmp/model",
           "--max-steps", a.max_steps, "--push", a.push]
print("$", " ".join(cmd + rest), flush=True); sys.exit(subprocess.call(cmd + rest))
