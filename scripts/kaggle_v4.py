"""Run BankDesk v4 jobs on Kaggle's free GPUs. No secrets leave this machine: models must download without a token.

  python3 scripts/kaggle_v4.py bundle FILE [FILE ...]        upload scripts/bankdesk_v4*.py plus the given data files
                                                             as the private dataset <user>/bankdesk-v4-bundle
  python3 scripts/kaggle_v4.py kernel SLUG "CMD" ["CMD" ...] push a private GPU kernel that runs the commands in a
                                                             folder holding the bundle; write results to out/
  python3 scripts/kaggle_v4.py wait SLUG                     block until the kernel ends; print its final status
  python3 scripts/kaggle_v4.py fetch SLUG DIR                download the kernel's out/ folder and log
In commands, `py` is the Python that has the libraries, the bundle files are in the current folder, and anything
written under out/ is kept.
"""
import glob, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
USER = json.load(open(os.path.expanduser("~/.kaggle/kaggle.json")))["username"]
DATASET = f"{USER}/bankdesk-v4-bundle"; WORK = os.path.join(ROOT, "runs", "bankdesk_v4", "kaggle")
PIP = '"transformers>=5.16.1,<5.21" "trl>=1.18,<1.19" peft datasets accelerate hf_transfer'


def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "outdated `kaggle` version" not in l)
    if check and r.returncode: sys.exit(f"FAILED: {cmd}\n{out}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "bundle":
        d = os.path.join(WORK, "bundle"); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        files = sorted(glob.glob(os.path.join(HERE, "bankdesk_v4*.py"))) + sys.argv[2:]
        for f in files: shutil.copy(f, d)
        json.dump({"title": "bankdesk-v4-bundle", "id": DATASET, "licenses": [{"name": "CC0-1.0"}]}, open(os.path.join(d, "dataset-metadata.json"), "w"))
        exists = DATASET in sh(f"kaggle datasets list --mine --search bankdesk-v4-bundle", check=False)
        print(sh(f'kaggle datasets version -p "{d}" -m "update" --dir-mode zip' if exists else f'kaggle datasets create -p "{d}" --dir-mode zip'))
        print("bundled", [os.path.basename(f) for f in files])
    elif cmd == "kernel":
        slug, cmds = sys.argv[2], sys.argv[3:]
        d = os.path.join(WORK, slug); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        code = f'''import glob, os, shutil, subprocess, sys, time
os.makedirs("/kaggle/working/job/out", exist_ok=True); os.chdir("/kaggle/working/job")
for f in glob.glob("/kaggle/input/**/*", recursive=True):
    if os.path.isfile(f): shutil.copy(f, ".")
print("bundle files:", sorted(os.listdir(".")), flush=True)
subprocess.run(sys.executable + " -m pip uninstall -y -q torchao", shell=True)     # Kaggle's torchao is too old for current peft
subprocess.run(sys.executable + " -m pip install -q " + {json.dumps(PIP)}, shell=True, check=True)
subprocess.run("nvidia-smi --query-gpu=name,memory.total --format=csv", shell=True)
env = dict(os.environ, HF_HUB_ENABLE_HF_TRANSFER="1", TOKENIZERS_PARALLELISM="false")
for c in {json.dumps(cmds)}:
    t = time.time(); r = subprocess.run(c.replace("py ", sys.executable + " ", 1) if c.startswith("py ") else c, shell=True, env=env)
    print("CMD_DONE exit", r.returncode, "minutes", round((time.time() - t) / 60, 1), "::", c[:120], flush=True)
shutil.copytree("out", "/kaggle/working/out", dirs_exist_ok=True)
for junk in ("/kaggle/working/job",): shutil.rmtree(junk, ignore_errors=True)
print("ALL_DONE", flush=True)
'''
        import ast; ast.parse(code)       # a kernel that does not parse wastes a GPU session
        open(os.path.join(d, "run.py"), "w").write(code)
        json.dump({"id": f"{USER}/{slug}", "title": slug, "code_file": "run.py", "language": "python", "kernel_type": "script",
                   "is_private": True, "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
                   "dataset_sources": [DATASET], "competition_sources": [], "kernel_sources": [], "model_sources": []},
                  open(os.path.join(d, "kernel-metadata.json"), "w"), indent=1)
        print(sh(f'kaggle kernels push -p "{d}"'))
    elif cmd == "wait":
        slug = sys.argv[2]; t0 = time.time()
        while time.time() - t0 < float(os.environ.get("V4_WAIT_MIN", "700")) * 60:
            s = sh(f"kaggle kernels status {USER}/{slug}", check=False)
            if any(x in s for x in ("COMPLETE", "ERROR", "CANCEL")): print("FINAL", s.strip(), "after", round((time.time() - t0) / 60), "min"); sys.exit(0)
            time.sleep(45)
        print("STILL RUNNING", s.strip())
    elif cmd == "fetch":
        slug, dest = sys.argv[2], sys.argv[3]; os.makedirs(dest, exist_ok=True)
        print(sh(f'kaggle kernels output {USER}/{slug} -p "{dest}"', check=False)[-600:])
