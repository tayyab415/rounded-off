"""Wait for the 24 per-family Adaption test-card jobs (data/bankdesk/adaption_test_jobs.json), download each finished one,
and append them to data/adaption/bankdesk_cards_{en,hi}_v2.jsonl. Stops after --max-min minutes, keeping what finished.
Usage: python3 scripts/adaption_collect_cards.py [--max-min 90]"""
import json, os, sys, time
from adaption import Adaption
key = os.environ.get("ADAPTION_API_KEY", "")
if not key:
    for l in open(os.path.expanduser("~/.config/adaption/env")):
        l = l.strip().removeprefix("export ").strip()
        if l.startswith("ADAPTION_API_KEY="): key = l.split("=", 1)[1].strip().strip("'\"")
c = Adaption(api_key=key)
jobs = json.load(open("data/bankdesk/adaption_test_jobs.json"))
pending = {(l, f): d for l, fam in jobs.items() for f, d in fam.items()}
done = {}; t0 = time.time(); maxmin = float(sys.argv[sys.argv.index("--max-min") + 1]) if "--max-min" in sys.argv else 90
os.makedirs("data/adaption/test_v2", exist_ok=True)
while pending and time.time() - t0 < maxmin * 60:
    for (l, f), d in list(pending.items()):
        try: st = c.datasets.get_status(d).status
        except Exception: continue
        if st in ("succeeded", "failed"):
            if st == "succeeded":
                p = f"data/adaption/test_v2/{l}_{f}.jsonl"; c.datasets.download(d, file_format="jsonl").write_to_file(p)
                done[(l, f)] = sum(1 for _ in open(p))
            else: done[(l, f)] = "failed"
            del pending[(l, f)]; print(time.strftime("%H:%M"), l, f, st, done[(l, f)], flush=True)
    if pending: time.sleep(60)
for l in ("en", "hi"):
    with open(f"data/adaption/bankdesk_cards_{l}_v2.jsonl", "w") as out:
        for f in jobs[l]:
            p = f"data/adaption/test_v2/{l}_{f}.jsonl"
            if os.path.exists(p): out.write(open(p).read())
print("still pending:", sorted(pending), flush=True)
