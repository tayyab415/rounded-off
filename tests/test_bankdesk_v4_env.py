"""Tests for the BankDesk v4 episode harness (scripts/bankdesk_v4_env.py)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bankdesk_v4 as g
import bankdesk_v4_env as e

WORLDS = [g.sample_world(f"e-{i}") for i in range(400)]
PAY = 'ACTION: decide(risk=low, action=pay, message="Done.")'


def test_parser_reads_forms_with_commas_and_brackets_in_the_wording():
    tool, args, err = e.parse('Sure.\nACTION: request_details(reference="Invoice number, and GSTIN (if a business)", met_payee=\'Have you met them?\')')
    assert (tool, err) == ("request_details", None) and args == {"reference": "Invoice number, and GSTIN (if a business)", "met_payee": "Have you met them?"}
    assert e.parse("ACTION: lookup(registry)")[:2] == ("lookup", {"what": "registry"})
    assert e.parse("ACTION: lookup(what=number)")[1] == {"what": "number"}
    assert e.parse('ACTION: decide(risk=high, action=hold, message="Please do not pay, call 1930')[1]["action"] == "hold"   # cut by the token limit
    assert e.parse("I will check.")[2]
    assert e.parse("ACTION: lookup(registry)\nACTION: request_details(purpose)\nACTION: decide(risk=low, action=pay)")[:2] == ("lookup", {"what": "registry"})
    assert e.parse("ACTION: request_details(purpose, reference, met_payee)")[1] == {"purpose": "", "reference": "", "met_payee": ""}
    assert e.parse('ACTION: request_details(purpose, reference="Invoice number, and GSTIN")')[1] == {"purpose": "", "reference": "Invoice number, and GSTIN"}
    assert e.parse("ACTION: lookup(registry)\n[Check] registry: found\nACTION: decide(risk=low, action=pay)")[0] == "lookup"   # imagined reply is cut


def test_reference_plays_cleanly_and_is_no_worse_than_the_greedy_policy():
    ws = WORLDS[:40]; eps = [e.run(w, e.reference_step) for w in ws]
    assert all(ep.end == "decided" and ep.outcome()["rejected"] == 0 for ep in eps)
    assert np.mean([ep.outcome()["utility"] for ep in eps]) >= np.mean([g.realised(w, *g.policy_reference(w)) for w in ws]) - 0.05


def test_expected_reward_matches_the_truth_on_average():
    """Scoring by the exact posterior must have the same mean as scoring against the hidden story."""
    for action, risk in (("pay", "low"), ("hold", "very_high")):
        outs = [e.run(w, e.agent_always(action, risk)).outcome() for w in [g.sample_world(f"u-{i}") for i in range(3000)]]
        exp = np.mean([o["reward"] for o in outs]); risk_part = np.mean([e.risk_term(risk, o["p_scam_at_decision"]) for o in outs])
        assert abs((exp - risk_part) - np.mean([o["utility"] for o in outs])) < 0.04, action


def test_a_lookup_of_something_the_customer_never_named_is_refused():
    w = next(w for w in WORLDS if w["cues"]["names_company"] == "no"); ep = e.Episode(w)
    assert "nothing to look up" in ep.step("ACTION: lookup(registry)") and ep.outcome()["rejected"] == 1 and not ep.lookups
    assert all(c[2] not in ("registry", "domain") for c in e.candidates(e.Episode(w)) if c[1] == "lookup")


def test_soft_targets_are_a_distribution_led_by_the_reference_action():
    for w in WORLDS[:6]:
        ep = e.Episode(w); st = e.soft_targets(ep)
        assert abs(sum(p for p, _ in st) - 1) < 1e-9 and all(p >= 0 for p, _ in st)
        ref = e.candidates(ep)[0]; mass = {}
        for p, c in st: mass[c[1]] = mass.get(c[1], 0) + p
        assert max(mass, key=mass.get) == ref[1]                                    # the reference's kind of action gets most weight
        assert next(c for p, c in st if c[1] == ref[1])[3] == ref[3]                # and the reference action leads within it


def test_one_form_per_case_and_field_limits():
    ep = e.Episode(WORLDS[0])
    assert "[Error]" in ep.step('ACTION: request_details(favourite_colour="?")')
    assert "[Error]" in ep.step('ACTION: request_details(purpose="a", met_payee="b", reference="c", on_call_now="d", told_secret="e", who_started="f")')
    assert ep.step('ACTION: request_details(purpose="What is this payment for?")').startswith("[Form] purpose:")
    assert "already sent" in ep.step('ACTION: request_details(met_payee="Have you met them?")')
    assert ep.outcome()["rejected"] == 3


def test_asking_for_a_secret_ends_the_case():
    for label in ("Please type the OTP you received", "अपना ओटीपी बताएं", "Enter your UPI PIN", "What is your card number and CVV?"):
        ep = e.Episode(WORLDS[1]); ep.step(f'ACTION: request_details(purpose="{label}")')
        assert ep.done and ep.secret_asked, label
        assert ep.outcome()["reward"] <= e.state_value(g.context(WORLDS[1]), {})[0] - e.SECRET_COST, label


def test_asking_about_a_secret_is_allowed():
    for label in ("Has anyone asked you to share an OTP, PIN or password?", "Did the caller ask you for your card number?",
                  "क्या किसी ने आपसे ओटीपी मांगा है?", "Invoice number or PIN code of the shop"):
        ep = e.Episode(WORLDS[1]); ep.step(f'ACTION: request_details(told_secret="{label}")')
        assert not ep.secret_asked and ep.fields == ["told_secret"], label


def test_parser_accepts_the_ways_a_strong_model_wrote_actions():
    assert e.parse('ACTION: decide(very_high, hold, message="We have placed a hold, please call 1930.")')[1] == {
        "message": "We have placed a hold, please call 1930.", "risk": "very_high", "action": "hold"}
    assert e.parse('ACTION: lookup(number="7347511968")')[1] == {"what": "number"}
    assert e.parse("ACTION: decide(risk=low, action=pay)")[1] == {"risk": "low", "action": "pay"}


def test_policy_table_bounds_the_decision():
    ep = e.Episode(WORLDS[2])
    assert "[Policy]" in ep.step('ACTION: decide(risk=very_high, action=pay, message="ok")') and not ep.done
    assert "[Policy]" in ep.step('ACTION: decide(risk=low, action=hold, message="no")') and not ep.done
    assert ep.step('ACTION: decide(risk=very_high, action=hold, message="no")') == "" and ep.action == "hold"
    assert all("pay" in e.POLICY[("low", s)] and "pay" not in e.POLICY[("very_high", s)] for s in g.STAKE)


def test_no_payment_while_an_answer_contradicts_the_records():
    w = next(w for w in WORLDS if w["answers"]["reference"] == "failed")
    ep = e.Episode(w); ep.step('ACTION: request_details(reference="Invoice number")')
    assert ep.contradicted() == ["reference"] and "CONTRADICTS" in ep.log[-1]["obs"]
    assert "[Policy]" in ep.step(PAY) and "pay" not in ep.allowed("low")


def test_running_out_of_turns_gets_the_safe_default_and_scores_below_a_chosen_delay():
    w = next(w for w in WORLDS if w["story"]["truth"] == "genuine"); ep = e.Episode(w)
    for _ in range(e.MAX_ACTIONS): ep.step("hello")
    o = ep.outcome()
    assert ep.end == "max_actions" and o["defaulted"] and o["action"] == e.SAFE_DEFAULT and o["rejected"] == e.MAX_ACTIONS
    chosen = e.run(w, e.agent_always("delay", "medium")) if "delay" in e.POLICY[("medium", w["records"]["stake"])] else None
    assert chosen and chosen.outcome()["reward"] > o["reward"] + e.SAFE_DEFAULT_COST


def test_reward_depends_on_what_the_form_asks():
    """The v3 flaw: any question earned the same reward. Here a form that asks the useful fields must beat a useless one."""
    good, useless, n = 0.0, 0.0, 0
    for w in WORLDS:
        ctx = g.context(w); fields = g.best_form(g.weights(ctx), ctx)[0]
        if len(fields) < 2 or w["records"]["call"] != "none" or w["records"]["bait_credits"] != "no": continue
        best = "ACTION: request_details(" + ", ".join(f'{f}="{e.FACTS[f][1]}"' for f in fields) + ")"
        junk = 'ACTION: request_details(on_call_now="Are you on a call?", bait_explain="What were the small credits?")'   # both "not applicable" here
        good += e.score_decision(w, [], best)[0]; useless += e.score_decision(w, [], junk)[0]; n += 1
    assert n >= 40 and good / n > useless / n + 0.1


def test_score_decision_is_exact_and_charges_a_rejected_sample():
    for w in WORLDS[5:9]:
        best = e.score_decision(w, [], e.reference_step(e.Episode(w)))[0]
        assert abs(best - e.state_value(g.context(w), {})[0]) < 1e-9            # the reference action is worth the state's value
        assert abs(e.score_decision(w, [], "let me think")[0] - (best - e.REJECT_COST)) < 1e-9
        assert e.score_decision(w, [], 'ACTION: decide(risk=low, action=pay, message="")')[0] <= best + 1e-9


def test_real_wording_replaces_the_template_and_shows_in_the_form():
    w = next(w for w in WORLDS if w["answers"]["reference"] == "failed")
    words = {"lang": "hi", "opening": "कृपया पैसे भेज दीजिए।", "answers": {"reference": "INV-00231", "purpose": "ऑर्डर का भुगतान"}}
    ep = e.Episode(w, words=words)
    assert ep.observation0().startswith("Customer (") and "कृपया पैसे भेज दीजिए।" in ep.observation0() and ep.case["lang"] == "hi"
    obs = ep.step('ACTION: request_details(reference="इनवॉइस नंबर", purpose="भुगतान किस लिए है?")')
    assert '"INV-00231" -> does not match any record (CONTRADICTS the records)' in obs and 'purpose: "ऑर्डर का भुगतान"' in obs
    assert w["answers"]["purpose"] not in obs        # with real wording the category is not shown; the agent has to read


def test_first_message_shows_records_but_not_the_story():
    for w in WORLDS[:60]:
        obs = e.first_observation(w)
        assert "[Records]" in obs and w["story"]["kind"] not in obs and "coaching" not in obs and "scam" not in obs.lower()


def test_names_and_template_text_do_not_depend_on_the_hidden_story():
    """The customer's words may carry the cues and nothing else. Same cue, same pool of text, scam or genuine."""
    ws = [g.sample_world(f"leak-{i}") for i in range(3000)]
    def seen(truth, key):
        out = {}
        for w in ws:
            if w["story"]["truth"] != truth: continue
            f = e.case_facts(w); op = e.template_opening(w, f)
            k = w["cues"]["opening"]
            out.setdefault(k, set()).add(op.split(". ")[1].split(" It is for")[0] if k != "bare" and ". " in op else "")
            out.setdefault("company", set()).add(f["company"])
        return out[key]
    for key in ("company", "benign_reason", "risky_reason"):
        assert seen("scam", key) == seen("genuine", key), key
