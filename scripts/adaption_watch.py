"""Poll Adaption datasets until each succeeds (or fails), then download it as JSONL. Exits when all are handled.
Usage: python3 adaption_watch.py OUT_DIR name=DATASET_ID [name=DATASET_ID ...]
"""
import os, sys, time
from adaption import Adaption
key = os.environ.get("ADAPTION_API_KEY", "")
if not key:
    for l in open(os.path.expanduser("~/.config/adaption/env")):
        l = l.strip().removeprefix("export ").strip()
        if l.startswith("ADAPTION_API_KEY="): key = l.split("=", 1)[1].strip().strip("'\"")
c = Adaption(api_key=key)
out = sys.argv[1]; todo = dict(a.split("=", 1) for a in sys.argv[2:])
deadline = time.time() + 3 * 3600
while todo and time.time() < deadline:
    for name, did in list(todo.items()):
        st = c.datasets.get_status(did)
        status = getattr(st, "status", None)
        if status in ("succeeded", "failed"):
            path = os.path.join(out, f"{name}.jsonl")
            try:
                c.datasets.download(did, file_format="jsonl").write_to_file(path)
                n = sum(1 for _ in open(path))
                print(f"{time.strftime('%H:%M:%S')} {name} {status}: {n} rows -> {path}", flush=True)
            except Exception as e:
                print(f"{name} {status}: download failed {e!r}", flush=True)
            del todo[name]
    if todo: time.sleep(60)
print("remaining:", todo or "none", flush=True)
