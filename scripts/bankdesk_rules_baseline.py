"""Bank-rules baseline for BankDesk v3: what a bank's own signal rules do on the same cards as the agent.

Each rule plays the real harness (bankdesk.Episode), with no model and no customer calls:
  1. ACTION: verify_payee(account=<payee account the customer shared>)
  2. ACTION: check_session()
  3. read the two [Bank check] lines the harness printed, count flags, then hold_and_escalate or do the task with the
     harness's own task steps (bankdesk._task_steps, the same steps as policy_do_task).
Flags (read from the printed checks, cross-checked against case.signals):
  name mismatch | account opened < 30 days ago | >= 10 incoming transfers in 24 h | customer on a phone call |
  screen-sharing app | new device
Rules:
  R_any     hold if any flag
  R_two     hold if 2 or more flags
  R_narrow  hold if screen-sharing app, or name mismatch, or (on a call AND account < 30 days old)
Rules never ask the customer, so the scripted customer is passed and never called.

Writes runs/bankdesk/rules/{R_any,R_two,R_narrow}.jsonl (normal checks) and .clean.jsonl (clean-check stress test), in
the bankdesk_run.py record format, then runs bankdesk_tables_v3.py over them plus the saved GRPO3 and R_wise50 test
episodes (normal and clean as separate rows) into runs/bankdesk/rules/TABLE_v3.md.
Usage: python3 -I scripts/bankdesk_rules_baseline.py [--cards data/bankdesk/cards_v3.jsonl] [--no-table]
"""
import argparse, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bankdesk as bd
from bankdesk_run import load_cases, summarize, print_table

ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "runs", "bankdesk", "rules")
MODEL_FILES = [  # saved model episodes, test split, 111 cards, LLM customer (checked in main before use)
    "results/raw/hf_runs/bankdesk/e374042/GRPO3.default.jsonl",
    "results/raw/hf_runs/bankdesk/e374042/GRPO3.default.clean.jsonl",
    "results/raw/hf_runs/bankdesk/311e670/R_wise50.default.jsonl",       # named in results/bankdesk_v3/FINAL_TEST.md
    "results/raw/hf_runs/bankdesk/e374042/R_wise50.default.clean.jsonl",
]
FLAG_NAMES = ("name_mismatch", "new_account", "busy_account", "on_call", "remote_app", "new_device")


def read_flags(payee_obs, session_obs):
    """Flags from the text the two bank checks printed (what any agent calling them would see)."""
    age = re.search(r"account opened (\d+) days ago", payee_obs)          # printed in days only when under 60 days
    inbound = re.search(r"(\d+) incoming transfers in the last 24 hours", payee_obs)
    assert "name check:" in payee_obs and inbound and "[Bank check] session:" in session_obs, (payee_obs, session_obs)
    return {"name_mismatch": "NO MATCH" in payee_obs,
            "new_account": bool(age) and int(age.group(1)) < 30,
            "busy_account": int(inbound.group(1)) >= 10,
            "on_call": "on a phone call for" in session_obs,
            "remote_app": "screen-sharing app detected" in session_obs,
            "new_device": "new device" in session_obs}


def flags_from_signals(s):
    return {"name_mismatch": not s["name_match"], "new_account": s["account_age_days"] < 30,
            "busy_account": s["inbound_24h"] >= 10, "on_call": s["on_call_min"] > 0,
            "remote_app": bool(s["remote_app"]), "new_device": bool(s["new_device"])}


RULES = {
    "R_any": lambda f: any(f.values()),
    "R_two": lambda f: sum(f.values()) >= 2,
    "R_narrow": lambda f: f["remote_app"] or f["name_mismatch"] or (f["on_call"] and f["new_account"]),
}


def play(case, rule):
    ep = bd.Episode(case, bd.scripted_customer)
    ep.step(f"ACTION: verify_payee(account={case.payee_account})")
    ep.step("ACTION: check_session()")
    payee_obs, session_obs = ep.log[0]["obs"], ep.log[1]["obs"]
    assert ep.log[0]["ok"] and ep.log[1]["ok"], case.case_id
    flags = read_flags(payee_obs, session_obs)
    assert flags == flags_from_signals(case.signals), (case.case_id, flags, case.signals)   # parser reads what was printed
    if RULES[rule](flags):
        why = ", ".join(k.replace("_", " ") for k in FLAG_NAMES if flags[k]) or "none"
        ep.step(f'ACTION: hold_and_escalate(reason="bank checks flagged: {why}")')
    while not ep.done:
        ep.step(bd._task_steps(ep))
    return ep, flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", default=os.path.join(ROOT, "data", "bankdesk", "cards_v3.jsonl"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--no-table", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    split_of = {json.loads(l)["card_id"]: json.loads(l)["split"] for l in open(a.cards, encoding="utf-8")}
    rule_files = []
    for signals in ("normal", "clean"):
        cases = load_cases(a.cards, a.split, signals=signals)
        assert cases and all(split_of[c.card_id] == a.split for c in cases)
        for rule in RULES:
            recs = []
            for c in cases:
                ep, flags = play(c, rule)
                recs.append(ep.record() | {"model": rule, "system": "none", "customer": "scripted", "signals": signals,
                                           "flags": flags})
            assert not any(r["n_questions"] for r in recs) and not any(r["rejected"] for r in recs)
            gen = [r for r in recs if r["variant"] == "genuine" and not r["false_escalation"]]
            assert all(r["completed"] for r in gen), "a non-held genuine case did not finish its task"
            path = os.path.join(OUT_DIR, f"{rule}.jsonl" if signals == "normal" else f"{rule}.clean.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
            rule_files.append(path)
            print_table(summarize(recs), f"{rule} ({a.split} split, {signals} checks, {len(recs)} episodes) -> {os.path.relpath(path, ROOT)}")
    if a.no_table: return
    model_files = [os.path.join(ROOT, p) for p in MODEL_FILES]
    for p in model_files:   # same split and same case set as the rule runs, so rows compare like for like
        recs = [json.loads(l) for l in open(p, encoding="utf-8")]
        assert {split_of[r["card_id"]] for r in recs} == {a.split}, p
        assert sorted(r["case_id"] for r in recs) == sorted(c.case_id for c in load_cases(a.cards, a.split)), p
    out = os.path.join(OUT_DIR, "TABLE_v3.md")
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "bankdesk_tables_v3.py"), out] + rule_files + model_files,
                   check=True, stdout=subprocess.DEVNULL)
    print(f"\ntable: {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
