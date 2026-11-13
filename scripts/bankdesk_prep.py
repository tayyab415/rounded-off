"""Scenario cards -> data/bankdesk/cards.jsonl with splits (design: notes/ENV_DESIGN.md section 4).

Two generators, so train and test never share one:
  test   every usable Adaption card (all 12 families, EN and native HI); the 3 held-out families are flagged
  train / dev   85 / 15 of the GLM-5.3-Flash cards (scripts/bankdesk_gen_cards.py; 9 families only, by opening hash)
English and Hindi cards are separate generations (Hindi written natively), so no translation pair crosses a split.
All four cases of a card stay together. Writes data/bankdesk/PREP_REPORT.md (counts, rejections, family balance).
Usage: python3 -I scripts/bankdesk_prep.py ADAPTION_EN ADAPTION_HI GLM_EN GLM_HI
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


def split_of(card, source):
    if source == "adaption": return "test"
    h = int(hashlib.sha256(card["opening"].strip().lower().encode()).hexdigest()[:8], 16) % 100
    return "train" if h < 85 else "dev"


os.makedirs(OUT, exist_ok=True)
report, kept, why = [], [], collections.Counter()
seen = set()
for source, lang, path in (("adaption", "en", sys.argv[1]), ("adaption", "hi", sys.argv[2]), ("glm", "en", sys.argv[3]), ("glm", "hi", sys.argv[4])):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    n_ok = 0
    for i, r in enumerate(rows):
        card = parse(r)
        if card is None: why[(f"{source} {lang}", "not JSON")] += 1; continue
        card["family"] = str(card.get("family", "")).strip().lower().replace(" ", "_").replace("-", "_")
        if card["family"] not in FAMILIES: why[(f"{source} {lang}", "unknown family")] += 1; continue
        probs = bd.validate_card(card)
        if probs: why[(f"{source} {lang}", probs[0])] += 1; continue
        key = card["opening"].strip().lower()
        if key in seen: why[(f"{source} {lang}", "duplicate opening")] += 1; continue
        seen.add(key)
        cid = f"{source[0]}{lang}-{hashlib.sha256(key.encode()).hexdigest()[:8]}"
        try: bd.cases_from_card(card, cid, lang)
        except Exception as e: why[(f"{source} {lang}", f"case build failed: {type(e).__name__}")] += 1; continue
        kept.append({"card_id": cid, "lang": lang, "split": split_of(card, source), "source": source, "family": card["family"],
                     "heldout_family": card["family"] in HELD_OUT, "card": card}); n_ok += 1
    report.append(f"- {source} {lang}: {len(rows)} generated, {n_ok} usable")

with open(f"{OUT}/cards.jsonl", "w", encoding="utf-8") as f:
    for k in kept: f.write(json.dumps(k, ensure_ascii=False) + "\n")

tab = collections.Counter((k["lang"], k["split"]) for k in kept)
famsrc = collections.Counter((k["lang"], k["family"], k["source"]) for k in kept)
lines = ["# BankDesk card prep", "", *report, "", "## Rejected", ""] + [f"- {l} {w}: {n}" for (l, w), n in sorted(why.items())] + \
        ["", "## Cards per split (x4 cases each)", "", "| lang | train (GLM) | dev (GLM) | test (Adaption) | of which held-out families |", "|---|---|---|---|---|"] + \
        [f"| {l} | " + " | ".join(str(tab[(l, s)]) for s in ("train", "dev", "test")) + f" | {sum(1 for k in kept if k['lang'] == l and k['split'] == 'test' and k['heldout_family'])} |" for l in ("en", "hi")] + \
        ["", "## Cards per family (train+dev GLM / test Adaption)", "", "| family | en | hi |", "|---|---|---|"] + \
        [f"| {fa}{' (held out)' if fa in HELD_OUT else ''} | {famsrc[('en', fa, 'glm')]} / {famsrc[('en', fa, 'adaption')]} | {famsrc[('hi', fa, 'glm')]} / {famsrc[('hi', fa, 'adaption')]} |" for fa in FAMILIES]
open(f"{OUT}/PREP_REPORT.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
