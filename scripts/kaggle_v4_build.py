"""Build a self-contained Kaggle kernel that runs BankDesk v4 models on a free GPU. No secrets go into the kernel.

  python3 scripts/kaggle_v4_build.py pilot runs/bankdesk_v4/kaggle_pilot \
      tyb343/rounded-off-bankdesk-grpo-v3=GRPO3 tyb343/rounded-off-tiny-aya-bank-sft-wiseft=R_wise50
  kaggle kernels push -p runs/bankdesk_v4/kaggle_pilot
The kernel carries the three v4 scripts as text, installs transformers, runs each model on worlds PREFIX-0..N-1 and
writes OUT/TAG.jsonl and TAG.summary.json to /kaggle/working/out. Models must download without a token.
"""
import base64, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["bankdesk_v4.py", "bankdesk_v4_env.py", "bankdesk_v4_run.py"]

if __name__ == "__main__":
    prefix, out, models = sys.argv[1], sys.argv[2], [m.split("=") for m in sys.argv[3:]]
    n = int(os.environ.get("V4_N", "48")); slug = os.environ.get("V4_SLUG", f"bankdesk-v4-{prefix}")
    os.makedirs(out, exist_ok=True)
    blobs = {f: base64.b64encode(open(os.path.join(HERE, f), "rb").read()).decode() for f in FILES}
    code = f'''import base64, json, os, subprocess, sys, time
FILES = {json.dumps(blobs)}
MODELS = {json.dumps(models)}
os.makedirs("/kaggle/working/v4", exist_ok=True); os.makedirs("/kaggle/working/out", exist_ok=True)
for name, b in FILES.items(): open("/kaggle/working/v4/" + name, "wb").write(base64.b64decode(b))
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers>=5.16.1,<5.21", "accelerate", "hf_transfer"], check=True)
subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv"])
env = dict(os.environ, HF_HUB_ENABLE_HF_TRANSFER="1", TOKENIZERS_PARALLELISM="false")
for repo, tag in MODELS:
    t = time.time()
    r = subprocess.run([sys.executable, "/kaggle/working/v4/bankdesk_v4_run.py", "--backend", "hf:" + repo, "--prefix", "{prefix}",
                        "--n", "{n}", "--out", "/kaggle/working/out/" + tag + ".jsonl", "--tag", tag], env=env)
    print("MODEL_DONE", tag, "exit", r.returncode, "minutes", round((time.time() - t) / 60, 1), flush=True)
    subprocess.run("rm -rf ~/.cache/huggingface/hub", shell=True)
print("ALL_DONE", flush=True)
'''
    open(os.path.join(out, "run.py"), "w").write(code)
    user = json.load(open(os.path.expanduser("~/.kaggle/kaggle.json")))["username"]
    json.dump({"id": f"{user}/{slug}", "title": slug, "code_file": "run.py", "language": "python", "kernel_type": "script",
               "is_private": True, "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
               "dataset_sources": [], "competition_sources": [], "kernel_sources": [], "model_sources": []},
              open(os.path.join(out, "kernel-metadata.json"), "w"), indent=1)
    print("built", out, "for", [m[1] for m in models], "kernel", f"{user}/{slug}")
