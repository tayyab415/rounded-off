"""Rupee view of BankDesk v3 episodes (illustrative): money sent to scammers and genuine customers blocked, per 1,000
requests, with each scam loss split between customer, RBI and the two banks under RBI's 2027 rules.

Per model x signals x language (EN, HI, both):
  scam side     rupees sent to the scam payee per 1,000 scam requests, and who carries them (customer, RBI, sending
                bank, beneficiary bank) under paragraphs 4(15A), 76N and 76T of the Commercial Banks Responsible
                Business Conduct Third Amendment Directions 2026 (in force 1 Jan 2027)
  genuine side  genuine customers blocked (false escalation) and genuine tasks not done, per 1,000 genuine requests
Loss split for one scam episode with loss L (sum of its transfers to the scam payee):
  L <= 50,000: 76T compensation min(0.85 L, 25,000); funded RBI 0.65 L, sending bank 0.10 L, beneficiary bank 0.10 L
               if L < 29,412, else RBI 19,118, sending bank 2,941, beneficiary bank 2,941. The customer bears the rest.
  L >  50,000: no 76T compensation; the customer bears all of it.
Assumes first claim, reported in time, no recoveries.

Amounts come from replaying each saved episode offline through scripts/bankdesk.py (the recorded customer answers are
fed back, no network); the replay must reproduce the saved outcome, or the script stops.
Usage: python3 -I scripts/bankdesk_rupee_view.py [--out results/bankdesk_v3/RUPEE_VIEW.md] [EPISODES.jsonl ...]
With no files it reads the rule baselines (runs/bankdesk/rules/) and the saved R_wise50 and GRPO3 test episodes.
"""
import argparse, collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bankdesk as bd
from bankdesk_run import load_cases

ROOT = os.path.dirname(HERE)
CARDS = os.path.join(ROOT, "data", "bankdesk", "cards_v3.jsonl")
ORDER = ["R_wise50", "GRPO3", "R_any", "R_two", "R_narrow"]
DEFAULT_FILES = [
    "results/raw/hf_runs/bankdesk/311e670/R_wise50.default.jsonl",
    "results/raw/hf_runs/bankdesk/e374042/R_wise50.default.clean.jsonl",
    "results/raw/hf_runs/bankdesk/e374042/GRPO3.default.jsonl",
    "results/raw/hf_runs/bankdesk/e374042/GRPO3.default.clean.jsonl",
] + [f"runs/bankdesk/rules/{r}{s}.jsonl" for r in ("R_any", "R_two", "R_narrow") for s in ("", ".clean")]
CAP_76T, FULL_CAP_FROM = 50_000, 29_412


def split_loss(L):
    """-> dict customer, rbi, sending, beneficiary (rupees) for one scam loss L under 76N/76T."""
    if L <= 0: return dict(customer=0.0, rbi=0.0, sending=0.0, beneficiary=0.0)
    if L > CAP_76T: return dict(customer=float(L), rbi=0.0, sending=0.0, beneficiary=0.0)
    if L < FULL_CAP_FROM: rbi, snd, ben = 0.65 * L, 0.10 * L, 0.10 * L
    else: rbi, snd, ben = 19_118.0, 2_941.0, 2_941.0
    comp = rbi + snd + ben
    assert abs(comp - min(0.85 * L, 25_000)) < 1, L
    return dict(customer=L - comp, rbi=rbi, sending=snd, beneficiary=ben)


def replay(rec, case):
    """Replay a saved episode through the harness with the recorded customer answers; return the transfers."""
    answers = iter([re.sub(r"\s*\(actions left: \d+\)$", "", t["obs"])[len("[Customer] "):]
                    for t in rec["turns"] if t["tool"] == "ask_customer" and t["ok"]])
    ep = bd.Episode(case, lambda c, q: next(answers))
    for t in rec["turns"]:
        if ep.done: break
        ep.step(t["raw"])
    o = ep.outcome()
    keys = ("money_to_scammer", "completed", "false_escalation", "end", "score")
    if any(o[k] != rec[k] for k in keys):
        sys.exit(f"replay of {rec.get('model')} {rec['case_id']} does not reproduce the saved outcome: "
                 f"{[(k, rec[k], o[k]) for k in keys if o[k] != rec[k]]}")
    return ep.transfers


def load(paths):
    split_of = {}
    for l in open(CARDS, encoding="utf-8"):
        r = json.loads(l); split_of[r["card_id"]] = r["split"]
    cases = {}
    groups = collections.defaultdict(list)       # (model, signals, split, lang) -> episode rows
    for p in paths:
        b = os.path.basename(p)
        sig_name = "clean" if (".clean." in b or b.endswith(".clean.jsonl")) else "normal"
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            sig = r.get("signals") or sig_name
            if sig != sig_name: sys.exit(f"{p}: record says signals={sig}, file name says {sig_name}")
            split = split_of[r["card_id"]]
            if (split, sig) not in cases:
                cases[(split, sig)] = {c.case_id: c for c in load_cases(CARDS, split, signals=sig)}
            case = cases[(split, sig)][r["case_id"]]
            tr = replay(r, case)
            loss = sum(t["amount"] for t in tr if t["account"] == case.payee_account) if r["variant"] == "scam" else 0
            row = {"variant": r["variant"], "loss": loss, "blocked": bool(r["false_escalation"]),
                   "done": bool(r["completed"]), "card_id": r["card_id"]}
            for lang in (r["lang"], "both"):
                groups[(r["model"], sig, split, lang)].append(row)
    return groups


def summarise(rows):
    sc = [r for r in rows if r["variant"] == "scam"]; ge = [r for r in rows if r["variant"] == "genuine"]
    per_s = 1000 / len(sc) if sc else 0; per_g = 1000 / len(ge) if ge else 0
    parts = collections.Counter()
    for r in sc:
        for k, v in split_loss(r["loss"]).items(): parts[k] += v
    return {"n_scam": len(sc), "paid": sum(r["loss"] > 0 for r in sc), "over_cap": sum(r["loss"] > CAP_76T for r in sc),
            "lost": sum(r["loss"] for r in sc) * per_s, **{k: v * per_s for k, v in parts.items()},
            "n_gen": len(ge), "blocked": sum(r["blocked"] for r in ge) * per_g,
            "not_done": sum(not r["done"] for r in ge) * per_g}


def rs(x): return f"{round(x):,}"


def amount_note():
    amts = collections.defaultdict(list)
    for l in open(CARDS, encoding="utf-8"):
        r = json.loads(l)
        if r["split"] == "test": amts[r["lang"]].append(bd.cases_from_card(r["card"], r["card_id"], r["lang"])[0].task["amount"])
    out = []
    for lang in ("en", "hi"):
        v = sorted(amts[lang])
        out.append(f"- {lang.upper()}: {len(v)} cards, Rs {v[0]:,} to Rs {v[-1]:,}, median Rs {v[len(v) // 2]:,}, "
                   f"{sum(x > CAP_76T for x in v)} above Rs 50,000")
    return "\n".join(out)


INTRO = """# Rupee view of BankDesk v3 (illustrative)

This page turns the BankDesk test results into rupees. For each agent it adds up the money sent to the scammer's
account, then splits each loss between the customer, RBI and the two banks under RBI's revised rules. It is an
illustration of scale. The amounts are the task amounts on our scenario cards, not real fraud data.

What was counted:
- Test split of `data/bankdesk/cards_v3.jsonl`: 111 cards, 4 cases each, so 222 scam and 222 genuine requests per run
  (EN 134 + 134, HI 88 + 88).
- Agents: R_wise50 is the repaired bank chat model before any agent training. GRPO3 is the trained agent. R_any,
  R_two and R_narrow are bank rules that read the two bank checks and nothing else (see `RULES_BASELINE.md`).
- "Normal" checks are the noisy v3 bank checks. "Clean" forces every check to look fine, so only a question to the
  customer can reveal the scam. The two are separate rows.
- Model episodes use the LLM customer. Rule episodes never ask, so no customer is called.
- Each saved episode was replayed offline through `scripts/bankdesk.py` with the recorded customer answers. Every replay
  reproduced the saved outcome. A loss L is the total the agent sent to the scam payee in that episode.

How a loss is split. RBI's revised rules in force from 1 Jan 2027 (Commercial Banks Responsible Business Conduct
Third Amendment Directions 2026, paragraphs 4(15A), 76N and 76T; checked against the RBI text):
- A payment the customer approved under coercion is a fraudulent transaction caused by customer negligence (76N). The
  customer bears the loss, minus any 76T compensation.
- 76T: if L is Rs 50,000 or less, compensation is min(0.85 x L, Rs 25,000), once per lifetime, if the victim reports
  to the bank and to 1930 or the cybercrime portal within 5 calendar days.
- Below Rs 29,412, RBI pays 0.65 x L, the sending bank 0.10 x L and the beneficiary bank 0.10 x L. From Rs 29,412 to
  Rs 50,000, RBI pays Rs 19,118 and each bank Rs 2,941, which adds up to the Rs 25,000 cap.
- Above Rs 50,000 there is no 76T compensation. The customer bears all of it.

Assumptions: every loss is the victim's first claim, reported in time, and nothing is recovered. One scam request is
one victim.

Card amounts on the test split:
{amounts}

Losses above Rs 50,000 get no compensation, so the few large cards carry much of the customer's share. Rows with few
paid scams (the "paid" column) rest on one to three episodes. There are no confidence intervals here. The percentage
tables in `RULES_BASELINE.md` have them.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--out")
    a = ap.parse_args()
    paths = [p if os.path.isabs(p) else os.path.join(ROOT, p) for p in (a.files or DEFAULT_FILES)]
    groups = load(paths)
    keys = sorted(groups, key=lambda k: (ORDER.index(k[0]) if k[0] in ORDER else len(ORDER), k[0], k[2] != "test", k[2],
                                         k[1] != "normal", ("en", "hi", "both").index(k[3])))
    S = {k: summarise(groups[k]) for k in keys}
    label = lambda k: (k[0], k[1] + ("" if k[2] == "test" else f", {k[2]} split"), k[3].upper() if k[3] != "both" else "both")

    scam = ["| agent | checks | lang | paid / scam requests | Rs lost | customer | RBI | sending bank | beneficiary bank | paid scams over Rs 50,000 (count) |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---|"]
    gen = ["| agent | checks | lang | genuine requests | blocked (false escalation) | not done |", "|---|---|---|---|---:|---:|"]
    for k in keys:
        s, (m, sig, lang) = S[k], label(k)
        scam.append(f"| {m} | {sig} | {lang} | {s['paid']} / {s['n_scam']} | {rs(s['lost'])} | {rs(s['customer'])} | "
                    f"{rs(s['rbi'])} | {rs(s['sending'])} | {rs(s['beneficiary'])} | {s['over_cap']} |")
        gen.append(f"| {m} | {sig} | {lang} | {s['n_gen']} | {s['blocked']:.0f} | {s['not_done']:.0f} |")
    body = ("## Per 1,000 scam requests: rupees sent to the scammer, and who carries them\n\n"
            "All rupee columns are per 1,000 scam requests. \"customer\" + \"RBI\" + the two banks = \"Rs lost\".\n\n"
            + "\n".join(scam) + "\n\n## Per 1,000 genuine requests: customers blocked and tasks not done\n\n"
            "\"not done\" counts every genuine request whose payment did not go through, blocked or not.\n\n" + "\n".join(gen) + "\n")
    print(body)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(INTRO.format(amounts=amount_note()) + "\nFiles: " + ", ".join(f"`{os.path.relpath(p, ROOT)}`" for p in paths)
                    + ".\nBuilt by `python3 -I scripts/bankdesk_rupee_view.py --out results/bankdesk_v3/RUPEE_VIEW.md`.\n\n" + body)
        print(f"wrote {os.path.relpath(a.out, ROOT) if os.path.isabs(a.out) else a.out}")


if __name__ == "__main__":
    main()
