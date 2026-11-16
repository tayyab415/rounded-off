"""Tests for the BankDesk v4 wording pipeline (scripts/bankdesk_v4_words.py). No network."""
import glob, json, os, sys
from collections import Counter
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bankdesk_v4 as g
import bankdesk_v4_env as e
import bankdesk_v4_words as W

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "bankdesk_v4")


def world_where(pred, prefix="t"):
    return next(w for w in (g.sample_world(f"{prefix}-{i}") for i in range(2000)) if pred(w))


def good_row(w, lang="en"):
    """A hand-built row that satisfies every code check, for testing the checks and the harness."""
    f = e.case_facts(w); gave = W.text_labels(w)["reference"] == "gave_reference"; code = W.ref_code(w["id"])
    op = f"Hello, pay Rs {f['amount']:,} to {f['payee']}, a/c {f['account']}."
    if f["company"] and f["company"] not in op: op += f" It is {f['company']}."
    if f["phone"]: op += f" Contact {f['phone']}."
    answers = {k: "No." for k in W.FIELD_ORDER} | {"reference": f"The code is {code}." if gave else "I have no bill.",
                                                  "purpose": "For my order."}
    if lang == "hi":
        op = f"नमस्ते, {f['payee']} को ₹{f['amount']} भेजना है, खाता {f['account']}।" + (f" कंपनी {f['company']}।" if f["company"] else "") \
             + (f" नंबर {f['phone']}।" if f["phone"] else "")
        answers = {k: "नहीं, ऐसा कुछ नहीं है।" for k in W.FIELD_ORDER} | {"reference": f"हाँ, बिल नंबर {code} है।" if gave else "कोई बिल नहीं है।"}
    if lang == "hinglish":
        op = f"bhai {f['payee']} ko {W.indian_commas(f['amount'])} bhejna hai, account {f['account']} mein." \
             + (f" {f['company']} ka hai." if f["company"] else "") + (f" number {f['phone']} hai." if f["phone"] else "")
        answers = {k: "nahi, aisa kuch nahi hai ji" for k in W.FIELD_ORDER} | {"reference": f"haan ji, {code} hai" if gave else "koi bill nahi hai ji"}
    return W.make_row(w, lang, W.GLM, {"opening": op, "answers": answers})


def test_amount_formats():
    assert W.amount_forms(232500) == ["2,32,500", "232,500", "232500"]
    for t in ("Send Rs 232500 now", "Rs. 232,500.", "₹2,32,500 bhejna hai", "232500"):
        assert W.has_amount(t, 232500), t
    for t in ("Rs 32,500", "Rs 2325000", "Rs 232,5000", "Rs 1,232,500", "2.32 lakh"):
        assert not W.has_amount(t, 232500), t
    assert W.indian_commas(500) == "500" and W.indian_commas(10_50_000) == "10,50,000"


def test_company_and_phone_iff_rules():
    w = world_where(lambda w: w["cues"]["names_company"] == "yes" and w["cues"]["names_number"] == "yes")
    row = good_row(w); assert W.code_checks(row, w) == []
    f = e.case_facts(w)
    assert "company_missing" in W.code_checks(row | {"opening": row["opening"].replace(f["company"], "them")}, w) or f["payee"] == f["company"]
    assert "phone_missing" in W.code_checks(row | {"opening": row["opening"].replace(f["phone"], "")}, w)
    spaced = f["phone"][:5] + " " + f["phone"][5:]
    assert W.code_checks(row | {"opening": row["opening"].replace(f["phone"], spaced)}, w) == []
    w2 = world_where(lambda w: w["cues"]["names_company"] == "no" and w["cues"]["names_number"] == "no" and w["cues"]["opening"] != "bare")
    row2 = good_row(w2); assert W.code_checks(row2, w2) == []
    assert "phone_named_but_not_in_story" in W.code_checks(row2 | {"opening": row2["opening"] + " Call 9876543210."}, w2)
    assert "company_named_but_not_in_story" in W.code_checks(row2 | {"opening": row2["opening"] + " For " + next(c for c in W.ALL_COMPANIES if " " in c) + "."}, w2)
    assert "extra_number" in W.code_checks(row2 | {"opening": row2["opening"] + " Paid 3 times already."}, w2)
    assert "account_missing" in W.code_checks(row2 | {"opening": row2["opening"].replace(e.case_facts(w2)["account"], "1234")}, w2)


def test_script_detection():
    w = world_where(lambda w: True)
    for lang in ("en", "hi", "hinglish"): assert W.code_checks(good_row(w, lang), w) == [], lang
    hi, en, hg = good_row(w, "hi"), good_row(w, "en"), good_row(w, "hinglish")
    assert "script:opening_not_devanagari" in W.code_checks(en | {"lang": "hi"}, w)
    assert "script:devanagari_in_latin_language" in W.code_checks(hi | {"lang": "en"}, w)
    assert "script:hinglish_reads_as_english" in W.code_checks(en | {"lang": "hinglish"}, w)
    assert "script:met_payee_not_devanagari" in W.code_checks(hi | {"answers": hi["answers"] | {"met_payee": "No, never met."}}, w)
    assert "devanagari_digits" in W.code_checks(hi | {"opening": hi["opening"] + " ९"}, w)
    assert "script:devanagari_in_latin_language" in W.code_checks(hg | {"answers": hg["answers"] | {"told_secret": "नहीं"}}, w)
    assert "stray_latin:met_payee" in W.code_checks(hi | {"answers": hi["answers"] | {"met_payee": "नहीं, personally नहीं मिला।"}}, w)


def test_empty_fields_are_dropped():
    w = world_where(lambda w: True); row = good_row(w)
    assert W.code_checks(row | {"opening": " "}, w) == ["empty:opening"]
    assert "empty:who_started" in W.code_checks(row | {"answers": row["answers"] | {"who_started": ""}}, w)
    assert "empty:purpose" in W.code_checks(row | {"answers": {k: v for k, v in row["answers"].items() if k != "purpose"}}, w)


def test_reference_codes_come_from_code_and_are_checked():
    ids = [f"{p}-{i}" for p, n in (("train", 600), ("dev", 100), ("rl", 500), ("pilot", 60)) for i in range(n)]
    codes = [W.ref_code(i) for i in ids]
    assert len(set(codes)) == len(codes) and codes == [W.ref_code(i) for i in ids]
    assert {W.ref_kind(c) for c in codes} == {"an invoice number", "an order number", "a bill number", "a booking reference", "a GSTIN"}
    assert "INV-48213" not in W.WRITER_SYSTEM and "ORD/2291/77" not in W.WRITER_SYSTEM
    w = world_where(lambda w: W.text_labels(w)["reference"] == "gave_reference"); row = good_row(w)
    assert W.ref_code(w["id"]) in W.writer_task(w, e.case_facts(w), "en")
    assert "reference_code_missing" in W.code_checks(row | {"answers": row["answers"] | {"reference": "INV-48213"}}, w)
    w2 = world_where(lambda w: W.text_labels(w)["reference"] == "none"); row2 = good_row(w2)
    assert W.ref_code(w2["id"]) not in W.writer_task(w2, e.case_facts(w2), "en")
    assert "reference_given_but_none" in W.code_checks(row2 | {"answers": row2["answers"] | {"reference": "No bill, only 4471"}}, w2)


def test_nothing_beyond_the_structure():
    bare = world_where(lambda w: w["cues"]["opening"] == "bare"); row = good_row(bare)
    assert "bare_has_urgency" in W.code_checks(row | {"opening": row["opening"] + " Please do it today."}, bare)
    assert "bare_has_urgency" in W.code_checks(row | {"opening": row["opening"] + " jaldi karo"}, bare)
    benign = world_where(lambda w: w["cues"]["opening"] == "benign_reason" and W.text_labels(w)["purpose"] == "goods_services")
    row = good_row(benign)
    assert "story_word:opening" in W.code_checks(row | {"opening": row["opening"] + " It is for my tasks."}, benign)
    assert "story_word:purpose" in W.code_checks(row | {"answers": row["answers"] | {"purpose": "To withdraw my earnings."}}, benign)
    assert "stray_name:who_started" in W.code_checks(row | {"answers": row["answers"] | {"who_started": "My friend Ramesh asked me."}}, benign)
    risky = world_where(lambda w: w["cues"]["opening"] == "risky_reason" and W.text_labels(w)["purpose"] == "fee_to_get_something")
    row = good_row(risky)
    assert W.code_checks(row | {"opening": row["opening"] + " I must pay the tax to withdraw my profits."}, risky) == []


def test_writer_never_sees_the_hidden_story():
    for i in range(300):
        w = g.sample_world(f"t-{i}"); task = W.writer_task(w, e.case_facts(w), W.assign_lang(w["id"]))
        assert "scam" not in task.lower() and "genuine" not in task.lower() and "coach" not in task.lower()
        if w["cues"]["opening"] != "risky_reason": assert "SITUATION" not in task
    # the task is a function of the structure only: swapping the hidden story changes nothing
    import copy
    stories = [{"truth": "scam", "kind": "digital_arrest", "coaching": 3}, {"truth": "genuine", "kind": "medical_urgent", "coaching": 0}]
    for i in range(300):
        w = g.sample_world(f"t-{i}"); lang = W.assign_lang(w["id"]); f = e.case_facts(w)
        tasks = set()
        for st in stories:
            w2 = copy.deepcopy(w); w2["story"] = st
            tasks.add(W.writer_task(w2, e.case_facts(w2), lang))
        assert len(tasks) == 1 and e.case_facts(w) == f
    # two worlds that differ only in the hidden story get the same task when nothing risky is told
    seen = {}
    for i in range(3000):
        w = g.sample_world(f"s-{i}")
        if w["cues"]["opening"] == "risky_reason": continue
        key = (json.dumps(w["cues"], sort_keys=True), json.dumps(W.text_labels(w), sort_keys=True))
        seen.setdefault(key, set()).add(w["story"]["truth"])
    assert any(len(v) == 2 for v in seen.values())


def test_duplicate_answers_are_dropped_past_the_limit():
    w = world_where(lambda w: True)
    long_no = "No, nobody has asked me anything like that at all."
    row = good_row(w); row = row | {"answers": {k: f"{long_no} ({k})" for k in W.FIELD_ORDER} | {"told_secret": long_no}}
    counts = Counter({("en", W.norm_answer(long_no)): W.DUP_LIMIT - 1})
    assert W.dup_check(row, counts) == []
    counts[("en", W.norm_answer(long_no))] += 1
    assert W.dup_check(row, counts) == ["duplicate_answer:told_secret"]
    assert W.dup_check(row | {"lang": "hi"}, counts) == []
    short = good_row(w)        # "No." in six fields: short answers may repeat up to SHORT_LIMIT, copies in the row count
    c2 = Counter({("en", "no"): W.SHORT_LIMIT - 6})
    assert W.dup_check(short, c2) == []
    c2[("en", "no")] += 1
    assert W.dup_check(short, c2) == ["duplicate_answer:who_started"]


def test_a_retry_gets_a_different_task():
    w = world_where(lambda w: True); f = e.case_facts(w); lang = W.assign_lang(w["id"])
    assert W.writer_task(w, f, lang, 0) == W.writer_task(w, f, lang)
    assert len({W.writer_task(w, f, lang, a) for a in range(3)}) == 3
    assert W.norm_answer("No,  nobody is on a call!") == W.norm_answer("no nobody is on a call")


def test_style_seed_is_deterministic_and_varied():
    seeds = [W.style_seed(f"train-{i}", "en") for i in range(200)]
    assert seeds == [W.style_seed(f"train-{i}", "en") for i in range(200)]
    assert len({(s["greeting"], s["start"], s["length"], s["typing"]) for s in seeds}) > 100
    assert all("lowercase" not in W.style_seed(f"train-{i}", "hi")["typing"] for i in range(200))


def test_language_and_writer_are_deterministic():
    ids = [f"pilot-{i}" for i in range(400)]
    assert [W.assign_lang(i) for i in ids] == [W.assign_lang(i) for i in ids]
    share = {l: sum(W.assign_lang(i) == l for i in ids) / len(ids) for l in ("en", "hi", "hinglish")}
    assert abs(share["en"] - .40) < .08 and abs(share["hi"] - .35) < .08 and abs(share["hinglish"] - .25) < .08
    assert W.writer_reviewer("pilot-4") == (W.GLM, W.DEEPSEEK) and W.writer_reviewer("pilot-7") == (W.DEEPSEEK, W.GLM)


def test_text_labels_hide_what_text_cannot_show():
    for i in range(300):
        w = g.sample_world(f"t-{i}"); lab = W.text_labels(w)
        assert set(lab) == {"opening"} | set(W.FIELD_ORDER)
        assert all(lab[k] in W.CATEGORIES[k] for k in lab)
        assert lab["reference"] == ("none" if w["answers"]["reference"] == "none" else "gave_reference")


def test_review_comparison():
    w = world_where(lambda w: True); lab = W.text_labels(w)
    assert W.compare(w, dict(lab)) == [] and W.compare(w, None) == ["review_unparsed"]
    flipped = dict(lab, opening="risky_reason" if lab["opening"] != "risky_reason" else "bare")
    assert W.compare(w, flipped) == [f"review:opening:{lab['opening']}->{flipped['opening']}"]


def test_parse_json_is_defensive():
    assert W.parse_json('```json\n{"opening": "a", "answers": {"x": "b"},}\n```') == {"opening": "a", "answers": {"x": "b"}}
    assert W.parse_json('<think>{"no": 1}</think> Sure: {"opening": "a {b}"} trailing') == {"opening": "a {b}"}
    assert W.parse_json("no json here") is None


def regime_hashes():
    old, out = g.REGIME, {}
    try:
        for reg in g.REGIMES: g.set_regime(reg); out[reg] = g.params_hash()
    finally:
        g.set_regime(old)
    return out


def test_rows_carry_the_generator_hash():
    w = world_where(lambda w: True)
    assert good_row(w)["world_hash"] == g.params_hash()
    hashes = regime_hashes(); assert g.params_hash() == hashes["base"] and len(set(hashes.values())) == len(hashes)
    for path in glob.glob(os.path.join(DATA, "words_*.jsonl")):
        if path.endswith(".rejected.jsonl"): continue
        split = os.path.basename(path)[len("words_"):-len(".jsonl")]       # words_shift.jsonl holds shift-regime worlds
        want = hashes[split if split in g.REGIMES else "base"]
        rows = [json.loads(l) for l in open(path)]
        v3 = [r for r in rows if r.get("prompt_version", 0) >= 3]
        assert all(r.get("world_hash") == want for r in v3), path


def test_structure_logit_is_the_exact_posterior_of_cues_and_answers():
    w = world_where(lambda w: w["records"]["call"] == "none" and w["answers"]["reference"] == "none")
    ctx = g.context(w)
    full = g.weights({k: ctx[k] for k in ("call", "bait_credits", "names_company", "names_number")} | w["cues"], None, w["answers"])
    # weights() with this ctx also multiplies the four records named in it; divide them back out
    for name in ("call", "bait_credits"):
        full = full / g.lik(g.RECORDS, name, ctx)[:, g.RECORDS[name][0].index(ctx[name])]
    p = g.p_scam_given(full)
    assert abs(W.structure_logit(w, payee_type=False) - np.log(p / (1 - p))) < 1e-6
    pt = g.lik(g.RECORDS, "payee_type", ctx)[:, g.RECORDS["payee_type"][0].index(ctx["payee_type"])]
    p2 = g.p_scam_given(full * pt)
    assert abs(W.structure_logit(w) - np.log(p2 / (1 - p2))) < 1e-6


def test_audit_catches_a_planted_leak_and_passes_clean_text():
    rows = []
    for i in range(400):
        w = g.sample_world(f"a-{i}"); r = good_row(w)
        rows.append(r)
    clean = W.audit(rows)
    assert abs(clean["gain"]) < 0.02 and clean["pass"]
    leaky = [r | {"opening": r["opening"] + (" zebra" if g.sample_world(r["id"])["story"]["truth"] == "scam" else " giraffe")} for r in rows]
    res = W.audit(leaky)
    assert res["gain"] > 0.1 and not res["pass"] and {"zebra", "giraffe"} & {t for t, _, _ in res["top_tokens"][:2]}


def test_kept_row_runs_through_the_episode_with_a_form():
    for lang in ("en", "hi", "hinglish"):
        w = world_where(lambda w: w["records"]["call"] != "none"); row = good_row(w, lang)
        assert W.code_checks(row, w) == []
        ep = e.Episode(w, words=row)
        assert row["opening"] in ep.observation0() and ep.case["lang"] == lang
        obs = ep.step('ACTION: request_details(reference="Invoice number", on_call_now="Is someone on a call with you?")')
        assert obs.startswith("[Form]") and row["answers"]["reference"] in obs and row["answers"]["on_call_now"] in obs
        ep.step('ACTION: decide(risk=high, action=hold, message="Held.")')
        assert ep.done and ep.outcome()["form_sent"] and ep.record()["lang"] == lang
