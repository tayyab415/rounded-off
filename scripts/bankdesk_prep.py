"""Adaption scenario-card exports -> data/bankdesk/cards.jsonl with splits (design: notes/ENV_DESIGN.md section 4).

English and Hindi cards are separate Adaption generations (Hindi written natively, not translated), so no card has a
translation on the other side of a split. Splits are by card; all four cases of a card stay together.
  test_heldout  every card of the held-out families (never trained on)
  train / dev / test   70 / 15 / 15 of the other families, by a hash of the card's opening
Also writes data/bankdesk/PREP_REPORT.md: counts, rejected cards and why, duplicates, family balance.
Usage: python3 -I scripts/bankdesk_prep.py EN_EXPORT.jsonl HI_EXPORT.jsonl
"""
import collections, hashlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd

FAMILIES = ("digital_arrest", "kyc_otp_update", "remote_access_refund", "task_job", "investment_crypto", "lottery_prize",
            "wrong_upi_collect", "relative_emergency", "safe_account", "marketplace_qr", "utility_disconnection", "loan_app_fee")
HELD_OUT = ("marketplace_qr", "relative_emergency", "loan_app_fee")
OUT = "data/bankdesk"


def parse(row):
    raw = row.get("enhanced_completion") or row.get("original_completion") or ""
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try: return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try: return json.loads(m.group(0))
            except json.JSONDecodeError: return None
    return None


def split_of(card):
    if card["family"] in HELD_OUT: return "test_heldout"
    h = int(hashlib.sha256(card["opening"].strip().lower().encode()).hexdigest()[:8], 16) % 100
    return "train" if h < 70 else "dev" if h < 85 else "test"


os.makedirs(OUT, exist_ok=True)
report, kept, why = [], [], collections.Counter()
for lang, path in (("en", sys.argv[1]), ("hi", sys.argv[2])):
    seen = set()
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    n_ok = 0
    for i, r in enumerate(rows):
        card = parse(r)
        if card is None: why[(lang, "not JSON")] += 1; continue
        card["family"] = str(card.get("family", "")).strip().lower().replace(" ", "_").replace("-", "_")
        if card["family"] not in FAMILIES: why[(lang, "unknown family")] += 1; continue
        probs = bd.validate_card(card)
        if probs: why[(lang, probs[0])] += 1; continue
        key = card["opening"].strip().lower()
        if key in seen: why[(lang, "duplicate opening")] += 1; continue
        seen.add(key)
        cid = f"{lang}-{hashlib.sha256(key.encode()).hexdigest()[:8]}"
        try: bd.cases_from_card(card, cid, lang)
        except Exception as e: why[(lang, f"case build failed: {type(e).__name__}")] += 1; continue
        kept.append({"card_id": cid, "lang": lang, "split": split_of(card), "family": card["family"], "card": card}); n_ok += 1
    report.append(f"- {lang}: {len(rows)} generated, {n_ok} usable")

with open(f"{OUT}/cards.jsonl", "w", encoding="utf-8") as f:
    for k in kept: f.write(json.dumps(k, ensure_ascii=False) + "\n")

tab = collections.Counter((k["lang"], k["split"]) for k in kept)
fam = collections.Counter((k["lang"], k["family"]) for k in kept)
lines = ["# BankDesk card prep", "", *report, "", "## Rejected", ""] + [f"- {l} {w}: {n}" for (l, w), n in sorted(why.items())] + \
        ["", "## Cards per split (x4 cases each)", "", "| lang | train | dev | test | test_heldout |", "|---|---|---|---|---|"] + \
        [f"| {l} | " + " | ".join(str(tab[(l, s)]) for s in ("train", "dev", "test", "test_heldout")) + " |" for l in ("en", "hi")] + \
        ["", "## Cards per family", "", "| family | en | hi |", "|---|---|---|"] + \
        [f"| {fa}{' (held out)' if fa in HELD_OUT else ''} | {fam[('en', fa)]} | {fam[('hi', fa)]} |" for fa in FAMILIES]
open(f"{OUT}/PREP_REPORT.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
