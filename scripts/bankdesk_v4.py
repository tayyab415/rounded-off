"""BankDesk v4, step 1: the world generator, the exact posterior, the reference policy and the baselines.

Structure only: no words, no model, no tools yet. Design: notes/BANKDESK_V4_DESIGN.md. Rule V4-1: PLAN.md.

A world is one payment request. Its hidden story is (truth, kind, coaching). Three layers of evidence follow from it:
  records  the bank's own data, fetched for free before the agent acts
  cues     what the customer's own words give away (free to anyone who can read them; the bank's records cannot)
  lookups  outside checks the agent may pay for (company registry, number reputation, domain age)
  fields   answers the customer would give to each possible form field
Every evidence value has a stated probability given the story, so P(scam | evidence) is exact (Bayes over the 33
stories). The reference policy plans greedily on top of that posterior: it buys a lookup or adds a form field only
while the expected gain is larger than the cost. "Reference", not "optimal": the posterior is exact, the planning is
greedy.

  python3 scripts/bankdesk_v4.py rule1 --n 20000 --out results/bankdesk_v4/RULE1.md
  python3 scripts/bankdesk_v4.py show --id demo-7
"""
import argparse, hashlib, json, os, random, sys
import numpy as np

# ---------------------------------------------------------------- stories
SCAM_KINDS = {"task_job": .22, "digital_arrest": .14, "investment": .16, "fake_company": .14, "safe_account": .12,
              "relative_emergency": .12, "marketplace": .10}
GEN_KINDS = {"routine_payee": .34, "new_vendor": .22, "new_individual": .20, "big_purchase": .12, "medical_urgent": .12}
COACH = {0: .25, 1: .30, 2: .30, 3: .15}    # 0 none, 1 given a cover purpose, 2 scripted answers, 3 scammer on a live call
STORIES = [("scam", k, c) for k in SCAM_KINDS for c in COACH] + [("genuine", k, 0) for k in GEN_KINDS]
IS_SCAM = np.array([s[0] == "scam" for s in STORIES])


def prior(p_scam=0.5):
    return np.array([p_scam * SCAM_KINDS[k] * COACH[c] if t == "scam" else (1 - p_scam) * GEN_KINDS[k] for t, k, c in STORIES])


def by_kind(table, default):
    """Evidence that depends on the story's kind only."""
    return lambda story, ev: table.get(story[1], default[story[0]] if isinstance(default, dict) else default)


def yn(p):   # (yes, no)
    return (p, 1 - p)


# ---------------------------------------------------------------- records: free, always fetched
S, G = "scam", "genuine"
RECORDS = {
    "paid_before": (("yes", "no"), by_kind({"routine_payee": yn(.97), "new_vendor": yn(.05), "new_individual": yn(.10),
                                             "big_purchase": yn(.03), "medical_urgent": yn(.05), "relative_emergency": yn(.06),
                                             "task_job": yn(.22), "investment": yn(.28)}, yn(.04))),
    "payee_age": (("new", "mid", "old"), by_kind({"routine_payee": (.01, .04, .95), "new_vendor": (.12, .23, .65),
                                                    "new_individual": (.06, .14, .80), "big_purchase": (.05, .15, .80),
                                                    "medical_urgent": (.03, .12, .85)}, (.50, .30, .20))),
    "payee_type": (("personal", "business"), by_kind({"task_job": yn(.85), "digital_arrest": yn(.80), "investment": yn(.60),
                                                       "fake_company": yn(.75), "safe_account": yn(.85), "relative_emergency": yn(.95),
                                                       "marketplace": yn(.80), "routine_payee": yn(.60), "new_vendor": yn(.30),
                                                       "new_individual": yn(.97), "big_purchase": yn(.35), "medical_urgent": yn(.25)}, yn(.5))),
    "senders_today": (("many", "few"), by_kind({"new_vendor": yn(.35), "big_purchase": yn(.30), "medical_urgent": yn(.40),
                                                 "new_individual": yn(.03), "routine_payee": yn(.12)}, yn(.45))),
    "fast_withdrawal": (("yes", "no"), by_kind({"new_vendor": yn(.10)}, {S: yn(.55), G: yn(.04)})),
    "reports": (("yes", "no"), by_kind({}, {S: yn(.12), G: yn(.01)})),
    "amount": (("usual", "high", "very_high"), by_kind({"routine_payee": (.85, .12, .03), "new_vendor": (.35, .45, .20),
                                                         "new_individual": (.45, .40, .15), "big_purchase": (.05, .35, .60),
                                                         "medical_urgent": (.15, .45, .40), "digital_arrest": (.08, .32, .60),
                                                         "safe_account": (.08, .32, .60)}, (.25, .40, .35))),
    "recent_change": (("yes", "no"), by_kind({"digital_arrest": yn(.65), "safe_account": yn(.65), "big_purchase": yn(.45),
                                               "medical_urgent": yn(.25)}, {S: yn(.35), G: yn(.06)})),
    "bait_credits": (("yes", "no"), by_kind({"task_job": yn(.70), "investment": yn(.50)}, {S: yn(.03), G: yn(.02)})),
    "call": (("none", "saved", "unsaved_long"),
             lambda st, ev: (.80, .15, .05) if st[0] == G else (.05, .05, .90) if st[2] == 3 else
             {"digital_arrest": (.35, .05, .60), "safe_account": (.40, .05, .55)}.get(st[1], (.70, .08, .22))),
    "screen_share": (("yes", "no"), by_kind({"safe_account": yn(.45), "fake_company": yn(.15)}, {S: yn(.08), G: yn(.02)})),
    "new_device": (("yes", "no"), by_kind({}, {S: yn(.10), G: yn(.06)})),
    "past_hold": (("yes", "no"), by_kind({}, {S: yn(.15), G: yn(.02)})),
    "stake": (("low", "mid", "high"), by_kind({"routine_payee": (.75, .20, .05), "new_vendor": (.50, .35, .15),
                                                "new_individual": (.60, .30, .10), "big_purchase": (.10, .40, .50),
                                                "medical_urgent": (.30, .40, .30), "digital_arrest": (.10, .30, .60),
                                                "safe_account": (.10, .30, .60)}, (.25, .40, .35))),
}
STAKE = {"low": .1, "mid": .4, "high": .9}       # share of the customer's savings that this payment moves

# ---------------------------------------------------------------- cues: only in the customer's words
def _opening(st, ev):                                                              # (bare, benign_reason, risky_reason)
    if st[0] == G: return {"routine_payee": (.55, .43, .02), "medical_urgent": (.30, .50, .20)}.get(st[1], (.45, .50, .05))
    return {0: (.35, .15, .50), 1: (.45, .40, .15), 2: (.40, .52, .08), 3: (.50, .45, .05)}[st[2]]


CUES = {
    "opening": (("bare", "benign_reason", "risky_reason"), _opening),
    "names_company": (("yes", "no"), by_kind({"fake_company": yn(.95), "task_job": yn(.80), "investment": yn(.80), "marketplace": yn(.20),
                                               "digital_arrest": yn(.10), "safe_account": yn(.15), "relative_emergency": yn(.05),
                                               "new_vendor": yn(.94), "big_purchase": yn(.83), "medical_urgent": yn(.83),
                                               "routine_payee": yn(.32), "new_individual": yn(.04)}, yn(.5))),
    "names_number": (("yes", "no"), by_kind({"marketplace": yn(.70), "routine_payee": yn(.35), "new_vendor": yn(.70),
                                              "new_individual": yn(.55), "big_purchase": yn(.50), "medical_urgent": yn(.45)}, yn(.85))),
}

# ---------------------------------------------------------------- lookups: the agent chooses, each costs LOOKUP_COST
LOOKUP_COST = 0.01
NA = (0, 0, 1)


def _gated(cue, table, default):
    """A lookup has something to look up only if the customer's story named it."""
    return lambda st, ev: NA if ev[cue] == "no" else table.get(st[1], default[st[0]] if isinstance(default, dict) else default)


LOOKUPS = {
    "registry": (("found", "not_found", "na"), _gated("names_company", {
        "fake_company": (.32, .65, .03), "task_job": (.25, .72, .03), "investment": (.37, .60, .03), "marketplace": (.25, .72, .03),
        "digital_arrest": (.50, .47, .03), "safe_account": (.65, .32, .03), "relative_emergency": (.40, .57, .03),
        "new_vendor": (.86, .11, .03), "big_purchase": (.88, .09, .03), "medical_urgent": (.94, .03, .03),
        "routine_payee": (.92, .05, .03), "new_individual": (.50, .47, .03)}, (.5, .47, .03))),
    "number": (("none", "some", "na"), _gated("names_number", {
        "task_job": (.42, .55, .03), "digital_arrest": (.33, .64, .03), "investment": (.50, .47, .03), "fake_company": (.48, .49, .03),
        "safe_account": (.36, .61, .03), "relative_emergency": (.60, .37, .03), "marketplace": (.64, .33, .03)}, (.94, .03, .03))),
    "domain": (("new", "old", "na"), _gated("names_company", {
        "fake_company": (.62, .10, .28), "investment": (.55, .12, .33), "task_job": (.55, .08, .37), "new_vendor": (.05, .55, .40),
        "big_purchase": (.04, .66, .30), "medical_urgent": (.02, .68, .30), "routine_payee": (.02, .50, .48),
        "new_individual": (.05, .25, .70)}, (.30, .10, .60))),
}

# ---------------------------------------------------------------- form fields: what the customer would answer
TRUE_PURPOSE = {"task_job": 1, "investment": 1, "fake_company": 1, "digital_arrest": 3, "safe_account": 3,
                "relative_emergency": 2, "marketplace": 0}                         # index into (goods, fee, known_person, other)
TELLS_TRUTH = {0: .85, 1: .35, 2: .12, 3: .06}                                     # by coaching level
COVER = np.array([.35, 0, .55, .10])


def _purpose(st, ev):
    if st[0] == G:
        return {"routine_payee": (.35, .01, .54, .10), "new_vendor": (.90, .01, .04, .05), "new_individual": (.05, .01, .89, .05),
                "big_purchase": (.85, .01, .04, .10), "medical_urgent": (.45, .01, .14, .40)}[st[1]]
    t = TELLS_TRUTH[st[2]]; one = np.zeros(4); one[TRUE_PURPOSE[st[1]]] = 1
    return tuple(t * one + (1 - t) * COVER)


def _met(st, ev):
    if st[0] == G:
        return yn({"routine_payee": .92, "new_vendor": .60, "new_individual": .93, "big_purchase": .50, "medical_urgent": .35}[st[1]])
    if st[1] == "relative_emergency": return yn(.85)                               # the victim believes it is their relative
    return yn({0: .05, 1: .30, 2: .60, 3: .72}[st[2]])


def _on_call(st, ev):                                                              # (yes, no, na); only asked usefully if the session shows a call
    if ev["call"] == "none": return (0, 0, 1)
    p = .92 if st[0] == G else {0: .60, 1: .40, 2: .15, 3: .08}[st[2]]
    return (p, 1 - p, 0)


def _bait(st, ev):                                                                 # (from_this_work, unrelated, na)
    if ev["bait_credits"] == "no": return (0, 0, 1)
    p = .05 if st[0] == G else {0: .80, 1: .60, 2: .30, 3: .20}[st[2]]
    return (p, 1 - p, 0)


def _how(st, ev):                                                                  # (bill_or_in_person, chat, phone)
    if st[0] == G:
        return {"routine_payee": (.75, .20, .05), "new_vendor": (.55, .38, .07), "new_individual": (.50, .40, .10),
                "big_purchase": (.70, .22, .08), "medical_urgent": (.80, .10, .10)}[st[1]]
    base = np.array({"task_job": (.03, .87, .10), "digital_arrest": (.02, .13, .85), "investment": (.04, .76, .20),
                     "fake_company": (.05, .60, .35), "safe_account": (.02, .13, .85), "relative_emergency": (.03, .57, .40),
                     "marketplace": (.05, .85, .10)}[st[1]])
    lie = {0: 0, 1: .15, 2: .35, 3: .45}[st[2]]
    return tuple((1 - lie) * base + lie * np.array([1, 0, 0]))


FIELDS = {   # name -> (values, likelihood, cost to a genuine customer: 0.03 a tap, 0.05 typed)
    "purpose": (("goods_services", "fee_to_get_something", "known_person", "other"), _purpose, .03),
    "met_payee": (("yes", "no"), _met, .03),
    "reference": (("verified", "failed", "none"), by_kind({
        "new_vendor": (.80, .05, .15), "big_purchase": (.72, .04, .24), "medical_urgent": (.55, .03, .42), "routine_payee": (.30, .02, .68),
        "new_individual": (.04, .03, .93), "fake_company": (.28, .40, .32), "investment": (.15, .45, .40),
        "relative_emergency": (.01, .04, .95), "marketplace": (.05, .25, .70), "digital_arrest": (.02, .18, .80),
        "safe_account": (.02, .18, .80)}, (.08, .47, .45)), .05),
    "on_call_now": (("yes", "no", "na"), _on_call, .03),
    "told_secret": (("yes", "no"), lambda st, ev: yn(.01) if st[0] == G else yn({0: .60, 1: .35, 2: .10, 3: .05}[st[2]]), .03),
    "bait_explain": (("from_this_work", "unrelated", "na"), _bait, .03),
    "how_got_details": (("bill_or_in_person", "chat_message", "phone_call"), _how, .03),
    "who_started": (("me", "someone_asked"), lambda st, ev: yn({"routine_payee": .55, "new_vendor": .45, "new_individual": .50,
                                                                  "big_purchase": .80, "medical_urgent": .50}[st[1]])
                    if st[0] == G else yn({0: .10, 1: .40, 2: .70, 3: .80}[st[2]]), .03),
}
MAX_FIELDS = 5
FIXED_FORM = ["purpose", "met_payee", "reference", "who_started", "told_secret"]
ABANDON_UTILITY = -0.5


def abandon(n_fields):
    """Chance a genuine customer gives up on a form of this length."""
    return 0.04 * max(0, n_fields - 2)


ACTIONS = ("pay", "delay", "hold")


def utility(action, scam, stake):
    """Outcome of the final action. A delay stops 60% of scams (the victim or the bank cancels within the hour)."""
    if scam: return {"pay": -(1 + stake), "hold": 1.0, "delay": .6 * 1.0 + .4 * -(1 + stake)}[action]
    return {"pay": 1.0, "delay": .6, "hold": -.6}[action]


CONTEXTS = [{"call": c, "bait_credits": b, "names_company": n, "names_number": m} for c in ("none", "unsaved_long")
            for b in ("yes", "no") for n in ("yes", "no") for m in ("yes", "no")]


def params_hash():
    """Hash of every rate above, so a frozen generator can be named."""
    blob = {"sharp": SHARP, "scam": SCAM_KINDS, "gen": GEN_KINDS, "coach": COACH, "stake": STAKE, "lookup_cost": LOOKUP_COST,
            "tables": {grp: {name: [list(map(float, spec[1](st, ctx))) for st in STORIES for ctx in CONTEXTS]
                             for name, spec in tbl.items()}
                       for grp, tbl in (("records", RECORDS), ("cues", CUES), ("lookups", LOOKUPS), ("fields", FIELDS))},
            "costs": {k: v[2] for k, v in FIELDS.items()}, "abandon": [abandon(n) for n in range(6)], "abandon_u": ABANDON_UTILITY,
            "utility": [[utility(a, s, x) for a in ACTIONS] for s in (True, False) for x in STAKE.values()]}
    return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()[:12]


# ---------------------------------------------------------------- sampling a world
def sample_world(world_id, p_scam=0.5):
    """Deterministic world for an id: the hidden story and every evidence value it would produce."""
    rnd = random.Random(int(hashlib.sha256(str(world_id).encode()).hexdigest()[:12], 16))
    pr = prior(p_scam); si = rnd.choices(range(len(STORIES)), weights=pr)[0]; st = STORIES[si]

    def draw(table, ev):
        out = {}
        for name, spec in table.items():
            out[name] = rnd.choices(spec[0], weights=lik(table, name, ev | out)[si])[0]
        return out
    records = draw(RECORDS, {}); cues = draw(CUES, records); ctx = records | cues
    return {"id": world_id, "story": {"truth": st[0], "kind": st[1], "coaching": st[2]}, "records": records, "cues": cues,
            "lookups": draw(LOOKUPS, ctx), "answers": draw(FIELDS, ctx)}


def context(world):
    """What is known before the agent acts: the bank's records and what the customer's words give away."""
    return world["records"] | world["cues"]


# ---------------------------------------------------------------- exact posterior
SHARP = {"records": 0.55, "cues": 1.0, "lookups": 0.75, "fields": 1.0}
_LAYER = {id(RECORDS): "records", id(CUES): "cues", id(LOOKUPS): "lookups", id(FIELDS): "fields"}
_LIK = {}


# Regimes. "base" is the world every model trains on. "shift" is a held-out test regime written down before any model
# saw it (PLAN.md, RULE V4-8): the bank's records are weaker evidence, more victims are coached, and the scam mix leans
# toward call-led scams. Every probability stays exact under each regime, so the reference policy knows the regime and
# a trained agent does not.
REGIMES = {
    "base": {"sharp_records": 0.55, "coach": {0: .25, 1: .30, 2: .30, 3: .15},
             "scam_kinds": {"task_job": .22, "digital_arrest": .14, "investment": .16, "fake_company": .14, "safe_account": .12,
                            "relative_emergency": .12, "marketplace": .10}},
    "shift": {"sharp_records": 0.35, "coach": {0: .10, 1: .25, 2: .35, 3: .30},
              "scam_kinds": {"task_job": .12, "digital_arrest": .24, "investment": .10, "fake_company": .10, "safe_account": .22,
                             "relative_emergency": .14, "marketplace": .08}},
}
REGIME = "base"


def set_regime(name):
    """Switch every rate to a regime, in place, and drop cached likelihoods. Changes params_hash()."""
    global REGIME
    r = REGIMES[name]; REGIME = name
    SHARP["records"] = r["sharp_records"]; COACH.clear(); COACH.update(r["coach"]); SCAM_KINDS.clear(); SCAM_KINDS.update(r["scam_kinds"])
    _LIK.clear()


def lik(table, name, ev):
    """Matrix [story, value] of P(value | story) for one evidence variable, given the records already known.
    Each raw table is blended with its own average over stories: SHARP = 1 keeps the table, lower values make the
    evidence weaker. One knob per layer, so a shifted test set can weaken a layer without touching the tables."""
    key = (_LAYER[id(table)], name, ev.get("call"), ev.get("bait_credits"), ev.get("names_company"), ev.get("names_number"),
           SHARP[_LAYER[id(table)]])
    if key not in _LIK:
        raw = np.array([table[name][1](st, ev) for st in STORIES], dtype=float); pr = prior(0.5); t = key[-1]
        _LIK[key] = t * raw + (1 - t) * (pr @ raw / pr.sum())
    return _LIK[key]


def weights(ctx, lookups=None, answers=None, p_scam=0.5):
    """Unnormalised posterior over the stories. `ctx` holds the records, and the cues if the reader has them."""
    w = prior(p_scam).copy()
    for table, obs in ((RECORDS, ctx), (CUES, ctx), (LOOKUPS, lookups or {}), (FIELDS, answers or {})):
        for name, val in obs.items():
            if name in table: w *= lik(table, name, ctx)[:, table[name][0].index(val)]
    return w


def p_scam_given(w): return float(w[IS_SCAM].sum() / w.sum())


def _u_matrix(stake, cost=0.0, q=0.0):
    """[action, story] utility. Friction (field costs, abandonment) falls on genuine customers only."""
    u = np.array([[utility(a, bool(s), stake) for s in IS_SCAM] for a in ACTIONS])
    u[:, ~IS_SCAM] = (1 - q) * u[:, ~IS_SCAM] + q * ABANDON_UTILITY - cost
    return u


def best_action(w, stake):
    eu = _u_matrix(stake) @ w / w.sum()
    return ACTIONS[int(eu.argmax())], float(eu.max())


def form_value(w, fields, records):
    """Expected utility of sending this form and then taking the best action for each possible set of answers."""
    stake = STAKE[records["stake"]]
    if not fields: return best_action(w, stake)[1]
    joint = w / w.sum()
    for f in fields:
        joint = joint[..., None] * lik(FIELDS, f, records).reshape((len(STORIES),) + (1,) * (joint.ndim - 1) + (-1,))
    u = _u_matrix(stake, cost=sum(FIELDS[f][2] for f in fields), q=abandon(len(fields)))
    return float(np.tensordot(u, joint, axes=(1, 0)).max(axis=0).sum())


def best_form(w, records, allowed=None):
    """Greedy: add the field with the largest gain while the gain is positive. Returns (fields, value)."""
    chosen, value = [], form_value(w, [], records)
    pool = [f for f in (allowed or FIELDS)]
    while len(chosen) < MAX_FIELDS:
        cand = [(form_value(w, chosen + [f], records), f) for f in pool if f not in chosen]
        if not cand: break
        v, f = max(cand)
        if v <= value + 1e-9: break
        chosen.append(f); value = v
    return chosen, value


def run_lookups(records, reveal, p_scam=0.5):
    """Greedy: buy a lookup while the expected value of the case afterwards (with its best form) beats the cost.
    `reveal(name)` returns the outcome of a bought lookup. Returns {name: outcome}."""
    got = {}
    while len(got) < len(LOOKUPS):
        w = weights(records, got, p_scam=p_scam); value = best_form(w, records)[1]; best = None
        for name in LOOKUPS:
            if name in got: continue
            L = lik(LOOKUPS, name, records); pv = (w[:, None] * L).sum(axis=0) / w.sum()
            ev = sum(pv[i] * best_form(w * L[:, i], records)[1] for i in range(L.shape[1]) if pv[i] > 0) - LOOKUP_COST
            if best is None or ev > best[0]: best = (ev, name)
        if best[0] <= value + 1e-9: break
        got[best[1]] = reveal(best[1])
    return got


# ---------------------------------------------------------------- policies. Each returns (lookups used, fields sent, action)
def realised(world, lookups_used, fields, action):
    """Utility of an episode. Expected over abandonment and over what a delay does; everything else is as sampled."""
    scam = world["story"]["truth"] == "scam"; stake = STAKE[world["records"]["stake"]]
    u = utility(action, scam, stake)
    if not scam:
        q = abandon(len(fields)); u = (1 - q) * u + q * ABANDON_UTILITY - sum(FIELDS[f][2] for f in fields)
    return u - LOOKUP_COST * len(lookups_used)


def policy_reference(world, p_scam=0.5):
    rec = context(world)
    got = run_lookups(rec, lambda name: world["lookups"][name], p_scam)
    fields, _ = best_form(weights(rec, got, p_scam=p_scam), rec)
    w = weights(rec, got, {f: world["answers"][f] for f in fields}, p_scam)
    return list(got), fields, best_action(w, STAKE[rec["stake"]])[0]


def policy_records_bayes(world, p_scam=0.5):
    return [], [], best_action(weights(world["records"], p_scam=p_scam), STAKE[world["records"]["stake"]])[0]


def policy_reader_bayes(world, p_scam=0.5):
    """A classifier that has the records and reads the customer's words perfectly, and does nothing else."""
    return [], [], best_action(weights(context(world), p_scam=p_scam), STAKE[world["records"]["stake"]])[0]


def policy_fixed_form(world, p_scam=0.5, only_if_worth_it=False):
    rec = context(world); w = weights(rec, p_scam=p_scam)
    if only_if_worth_it and form_value(w, FIXED_FORM, rec) <= form_value(w, [], rec):
        return [], [], best_action(w, STAKE[rec["stake"]])[0]
    w = weights(rec, None, {f: world["answers"][f] for f in FIXED_FORM}, p_scam)
    return [], list(FIXED_FORM), best_action(w, STAKE[rec["stake"]])[0]


def policy_rules(world, p_scam=0.5):
    r = world["records"]
    flag = (r["reports"] == "yes" or r["screen_share"] == "yes" or r["call"] == "unsaved_long" or r["fast_withdrawal"] == "yes"
            or (r["payee_age"] == "new" and r["senders_today"] == "many"))
    return [], [], "hold" if flag else "pay"


def single_cues():
    return [(name, val, act) for name, spec in RECORDS.items() for val in spec[0] for act in ("hold", "delay")]


def policy_cue(cue):
    name, val, act = cue
    return lambda world, p_scam=0.5: ([], [], act if world["records"][name] == val else "pay")


def mean_utility(worlds, policy, p_scam=0.5):
    return float(np.mean([realised(w, *policy(w, p_scam)) for w in worlds]))


# ---------------------------------------------------------------- Rule V4-1
def rule1(n, seed="v4", p_scam=0.5):
    worlds = [sample_world(f"{seed}-{i}", p_scam) for i in range(n)]
    half = n // 2; fit, held = worlds[:half], worlds[half:]
    cue = max(single_cues(), key=lambda c: mean_utility(fit, policy_cue(c), p_scam))
    runs = {}
    for name, pol in [("always pay", lambda w, p: ([], [], "pay")), ("always hold", lambda w, p: ([], [], "hold")),
                      (f"best single cue ({cue[2]} if {cue[0]} = {cue[1]})", policy_cue(cue)), ("bank rules", policy_rules),
                      ("Bayes on records", policy_records_bayes), ("Bayes on records + customer's words", policy_reader_bayes),
                      ("Bayes + fixed form for everyone", policy_fixed_form),
                      ("Bayes + fixed form when worth it", lambda w, p: policy_fixed_form(w, p, True)),
                      ("reference", policy_reference)]:
        eps = [(w, pol(w, p_scam)) for w in held]
        scams = [x for x in eps if x[0]["story"]["truth"] == "scam"]; gens = [x for x in eps if x[0]["story"]["truth"] == "genuine"]
        runs[name] = {"u": float(np.mean([realised(w, *e) for w, e in eps])),
                      "scam_paid": 100 * np.mean([e[2] == "pay" for _, e in scams]),
                      "gen_paid": 100 * np.mean([e[2] == "pay" for _, e in gens]),
                      "gen_held": 100 * np.mean([e[2] == "hold" for _, e in gens]),
                      "gen_no_form": 100 * np.mean([not e[1] for _, e in gens]),
                      "fields_gen": float(np.mean([len(e[1]) for _, e in gens])),
                      "fields_scam": float(np.mean([len(e[1]) for _, e in scams])),
                      "lookups": float(np.mean([len(e[0]) for _, e in eps])),
                      "paid_by_coach": {c: 100 * float(np.mean([e[2] == "pay" for w, e in scams if w["story"]["coaching"] == c])) for c in COACH},
                      "forms": len({tuple(e[1]) for _, e in eps})}
    floor = max(runs["always pay"]["u"], runs["always hold"]["u"]); ref = runs["reference"]["u"]
    for r in runs.values(): r["closure"] = 100 * (r["u"] - floor) / (ref - floor)
    names = list(runs); cue_name = names[2]
    checks = {"a: best single cue <= 50% closure": runs[cue_name]["closure"] <= 50,
              "b: bank rules <= 60% closure": runs["bank rules"]["closure"] <= 60,
              "c: Bayes on records <= 75% closure": runs["Bayes on records"]["closure"] <= 75,
              "d: fixed form for everyone >= 0.02 below reference": ref - runs["Bayes + fixed form for everyone"]["u"] >= .02,
              "e: reference sends no form to >= 30% of genuine": runs["reference"]["gen_no_form"] >= 30}
    return {"n_held": len(held), "p_scam": p_scam, "hash": params_hash(), "runs": runs, "checks": checks}


def rule1_markdown(res):
    L = [f"# Rule V4-1: is the generator hard enough?\n", f"Generator hash `{res['hash']}`. {res['n_held']} held-out worlds, scam rate "
         f"{res['p_scam']:.0%}. Structure only: every policy below reads exact probabilities; no language model is involved.\n",
         "| policy | utility per case | closure % | scams paid % | genuine paid % | genuine held % | genuine with no form % | fields per genuine | lookups |",
         "|---|---|---|---|---|---|---|---|---|"]
    for name, r in res["runs"].items():
        L.append(f"| {name} | {r['u']:.3f} | {r['closure']:.0f} | {r['scam_paid']:.1f} | {r['gen_paid']:.1f} | {r['gen_held']:.1f} | "
                 f"{r['gen_no_form']:.0f} | {r['fields_gen']:.2f} | {r['lookups']:.2f} |")
    ref = res["runs"]["reference"]
    L += ["", "Scams paid by the reference policy, by coaching level (no bar): " +
          ", ".join(f"level {c}: {v:.1f}%" for c, v in ref["paid_by_coach"].items()) + ".",
          f"Distinct forms the reference sent: {ref['forms']}.", "", "| check | result |", "|---|---|"]
    L += [f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in res["checks"].items()]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("rule1"); a1.add_argument("--n", type=int, default=20000); a1.add_argument("--out"); a1.add_argument("--seed", default="v4")
    a2 = sub.add_parser("show"); a2.add_argument("--id", default="demo-1")
    a = ap.parse_args()
    if a.cmd == "rule1":
        res = rule1(a.n, a.seed); md = rule1_markdown(res); print(md)
        if a.out:
            os.makedirs(os.path.dirname(a.out), exist_ok=True); open(a.out, "w").write(md)
            json.dump(res, open(a.out.replace(".md", ".json"), "w"), indent=1, default=float)
        sys.exit(0 if all(res["checks"].values()) else 1)
    w = sample_world(a.id); lk, fields, act = policy_reference(w)
    print(json.dumps(w, indent=1)); print("P(scam | records) =", round(p_scam_given(weights(w["records"])), 3),
                                          "| with the customer's words =", round(p_scam_given(weights(context(w))), 3))
    print("reference policy: lookups", lk, "| form", fields, "| action", act)
