"""Tests for the BankDesk v4 generator and reference policy (scripts/bankdesk_v4.py)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bankdesk_v4 as b

WORLDS = [b.sample_world(f"t-{i}") for i in range(6000)]


def test_every_distribution_sums_to_one():
    for table in (b.RECORDS, b.CUES, b.LOOKUPS, b.FIELDS):
        for name in table:
            for ctx in b.CONTEXTS:
                    m = b.lik(table, name, ctx)
                    assert m.shape == (len(b.STORIES), len(table[name][0])) and np.allclose(m.sum(axis=1), 1) and (m >= 0).all(), name


def test_world_is_deterministic_and_complete():
    assert b.sample_world("x-1") == b.sample_world("x-1") != b.sample_world("x-2")
    w = b.sample_world("x-1")
    assert set(w["records"]) == set(b.RECORDS) and set(w["lookups"]) == set(b.LOOKUPS) and set(w["answers"]) == set(b.FIELDS)
    assert set(w["cues"]) == set(b.CUES)
    for x in WORLDS[:500]:      # an outside check has nothing to find unless the customer's story named it
        assert (x["lookups"]["registry"] == "na") or x["cues"]["names_company"] == "yes"
        assert (x["lookups"]["number"] == "na") or x["cues"]["names_number"] == "yes"


def test_scam_rate_matches_the_prior():
    assert abs(np.mean([w["story"]["truth"] == "scam" for w in WORLDS]) - 0.5) < 0.02


def _calibrated(probs, truth):
    """In every probability band the share of scams must match the stated probability, within 4 standard errors."""
    probs, truth = np.array(probs), np.array(truth)
    for lo in np.arange(0, 1, 0.1):
        sel = (probs >= lo) & (probs < lo + 0.1)
        if sel.sum() < 100: continue
        p = probs[sel].mean(); se = np.sqrt(p * (1 - p) / sel.sum())
        assert abs(p - truth[sel].mean()) < 4 * se + 0.005, (lo, p, truth[sel].mean(), int(sel.sum()))


def test_posterior_is_calibrated_on_records():
    _calibrated([b.p_scam_given(b.weights(w["records"])) for w in WORLDS], [w["story"]["truth"] == "scam" for w in WORLDS])


def test_posterior_is_calibrated_with_the_customers_words():
    _calibrated([b.p_scam_given(b.weights(b.context(w))) for w in WORLDS], [w["story"]["truth"] == "scam" for w in WORLDS])


def test_posterior_is_calibrated_with_lookups_and_answers():
    _calibrated([b.p_scam_given(b.weights(b.context(w), w["lookups"], w["answers"])) for w in WORLDS],
                [w["story"]["truth"] == "scam" for w in WORLDS])


def test_empty_form_equals_best_action():
    for w in WORLDS[:50]:
        wt = b.weights(w["records"])
        assert abs(b.form_value(wt, [], w["records"]) - b.best_action(wt, b.STAKE[w["records"]["stake"]])[1]) < 1e-12


def test_free_information_never_hurts(monkeypatch):
    monkeypatch.setattr(b, "FIELDS", {k: (v[0], v[1], 0.0) for k, v in b.FIELDS.items()})
    monkeypatch.setattr(b, "abandon", lambda n: 0.0)
    monkeypatch.setattr(b, "_LAYER", b._LAYER | {id(b.FIELDS): "fields"})
    for w in WORLDS[:40]:
        wt = b.weights(b.context(w)); base = b.form_value(wt, [], b.context(w))
        for f in b.FIELDS: assert b.form_value(wt, [f], b.context(w)) >= base - 1e-9


def test_best_form_is_bounded_and_never_worse_than_no_form():
    for w in WORLDS[:150]:
        ctx = b.context(w); wt = b.weights(ctx); fields, value = b.best_form(wt, ctx)
        assert len(fields) <= b.MAX_FIELDS and len(set(fields)) == len(fields)
        assert value >= b.form_value(wt, [], ctx) - 1e-12
        assert abs(value - b.form_value(wt, fields, ctx)) < 1e-12


def test_friction_falls_on_genuine_customers_only():
    gen = next(w for w in WORLDS if w["story"]["truth"] == "genuine"); scam = next(w for w in WORLDS if w["story"]["truth"] == "scam")
    assert b.realised(gen, [], ["purpose", "reference", "met_payee"], "pay") < b.realised(gen, [], [], "pay")
    assert b.realised(scam, [], ["purpose", "reference", "met_payee"], "hold") == b.realised(scam, [], [], "hold")
    assert b.realised(gen, ["registry"], [], "pay") == b.realised(gen, [], [], "pay") - b.LOOKUP_COST


def test_policies_rank_as_the_rule_expects():
    ws = WORLDS[:1200]
    ref, reader, bayes, rules = (b.mean_utility(ws, p) for p in (b.policy_reference, b.policy_reader_bayes, b.policy_records_bayes, b.policy_rules))
    assert ref > reader > bayes > rules > max(b.mean_utility(ws, lambda w, p: ([], [], a)) for a in ("pay", "hold"))


def test_weaker_records_make_the_records_classifier_worse():
    ws = WORLDS[:1500]; before = b.mean_utility(ws, b.policy_records_bayes); old = b.SHARP["records"]
    try:
        b.SHARP["records"] = 0.2
        shifted = [b.sample_world(f"s-{i}") for i in range(1500)]
        assert b.mean_utility(shifted, b.policy_records_bayes) < before
    finally:
        b.SHARP["records"] = old
