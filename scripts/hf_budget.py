"""Hard spending guard for Hugging Face Jobs (cap set by Tayyab: $12; his balance is $14, so never cross it).

Counts every Job created since START (older jobs belong to earlier projects and are already billed), prices it at the
flavor's hourly rate from the Jobs hardware list, and treats a running or queued job as running until its timeout
(worst case). Manual entries (e.g. Inference Providers calls) live in notes/hf_spend_manual.json.

  python scripts/hf_budget.py status
  python scripts/hf_budget.py launch FLAVOR TIMEOUT_MIN -- <args for `hf jobs uv run` after the flavor/timeout>
      refuses unless spent + worst case of running jobs + FLAVOR x TIMEOUT_MIN fits under the cap
  python scripts/hf_budget.py watch [--every 120]
      polls; cancels every running job of ours if spent + accrued + margin reaches the cap
Every launch gets --timeout (so cost is bounded even if this machine sleeps) and the label project=rounded-off.
"""
import datetime as dt, json, os, subprocess, sys, time
from huggingface_hub import HfApi

CAP = 12.00          # USD, hard
MARGIN = 0.50        # watch mode cancels when within this of the cap
START = dt.datetime(2026, 11, 13, 13, 0, tzinfo=dt.timezone.utc)    # 18:30 IST, Nov 13 (before our first job)
LABEL = ("project", "rounded-off")
MANUAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "notes", "hf_spend_manual.json")
FALLBACK = {"cpu-basic": 0.01, "cpu-upgrade": 0.03, "t4-small": 0.40, "t4-medium": 0.60, "l4x1": 0.80, "a10g-small": 1.00,
            "a10g-large": 1.50, "l40sx1": 1.80, "a100-large": 2.50, "rtx-pro-6000": 2.75, "h200": 5.00}
api = HfApi()

def prices():
    p = dict(FALLBACK)
    try:
        for h in api.list_jobs_hardware():
            unit = {"minute": 60, "hour": 1, "second": 3600}.get(getattr(h, "unit_label", None))
            if h.name and h.unit_cost_usd and unit: p[h.name] = max(p.get(h.name, 0), float(h.unit_cost_usd) * unit)
    except Exception:
        pass
    return p

def _t(x):
    if x is None: return None
    if isinstance(x, str): x = dt.datetime.fromisoformat(x.replace("Z", "+00:00"))
    return x if x.tzinfo else x.replace(tzinfo=dt.timezone.utc)

def _stage(j):
    s = j.status
    return (getattr(s, "stage", None) or (s.get("stage") if isinstance(s, dict) else s) or "").upper()

def ledger():
    P, now, rows = prices(), dt.datetime.now(dt.timezone.utc), []
    for j in api.list_jobs():
        created = _t(j.created_at)
        if created is None or created < START: continue
        rate = P.get(str(j.flavor), max(P.values()))
        stage = _stage(j)
        end = _t(getattr(j, "finished_at", None))
        live = stage not in ("COMPLETED", "ERROR", "CANCELED", "CANCELLED", "DELETED", "FAILED", "TIMEOUT")  # anything unfinished
        started = _t(getattr(j, "started_at", None))
        if started is None and stage in ("RUNNING", "COMPLETED", "ERROR", "TIMEOUT"): started = created   # unknown: be conservative
        spent = rate * max(0.0, ((end or now) - started).total_seconds()) / 3600 if started else 0.0     # queue time is not billed
        timeout = getattr(j, "timeout", None) or (j.labels or {}).get("timeout_min")
        worst = rate * float(timeout) / 60 if (live and timeout) else (rate * 6 if live else spent)  # unknown timeout: assume 6 h
        rows.append(dict(id=j.id, flavor=str(j.flavor), stage=stage, spent=spent, worst=max(worst, spent), live=live))
    manual = json.load(open(MANUAL)) if os.path.exists(MANUAL) else []
    return rows, sum(m["usd"] for m in manual), P

def summary():
    rows, manual, P = ledger()
    spent = sum(r["spent"] for r in rows) + manual
    worst = sum(r["worst"] for r in rows) + manual
    return rows, spent, worst, P

def status():
    rows, spent, worst, _ = summary()
    for r in rows: print(f"{r['id']}  {r['flavor']:<12} {r['stage']:<10} spent ${r['spent']:.2f}  worst ${r['worst']:.2f}")
    print(f"spent ${spent:.2f}  worst case incl. running ${worst:.2f}  cap ${CAP:.2f}  headroom ${CAP - worst:.2f}")
    return spent, worst

def launch(flavor, minutes, rest):
    rows, spent, worst, P = summary()
    if flavor not in P: sys.exit(f"unknown flavor {flavor}")
    new = P[flavor] * minutes / 60
    print(f"spent ${spent:.2f}, running worst ${worst - spent:.2f}, this job worst ${new:.2f} ({flavor} x {minutes} min)")
    if worst + new > CAP: sys.exit(f"REFUSED: ${worst + new:.2f} would exceed the ${CAP:.2f} cap")
    cmd = ["hf", "jobs", "uv", "run", "--flavor", flavor, "--timeout", f"{int(minutes)}m",
           "--label", f"{LABEL[0]}={LABEL[1]}", "--label", f"timeout_min={int(minutes)}", *rest]
    print("launching:", " ".join(cmd)); sys.exit(subprocess.call(cmd))

def watch(every):
    while True:
        rows, spent, worst, _ = summary()
        live = [r for r in rows if r["live"]]
        print(f"{dt.datetime.now():%H:%M} spent ${spent:.2f} live {len(live)}", flush=True)
        if live and spent + MARGIN >= CAP:
            for r in live:
                print("CANCEL", r["id"], flush=True); subprocess.call(["hf", "jobs", "cancel", r["id"]])
        time.sleep(every)

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "status": status()
    elif a[0] == "launch": launch(a[1], float(a[2]), a[a.index("--") + 1:] if "--" in a else a[3:])
    elif a[0] == "watch": watch(int(a[a.index("--every") + 1]) if "--every" in a else 120)
    else: sys.exit(__doc__)
