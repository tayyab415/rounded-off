"""BankDesk v4, step 2: the episode harness. Design: notes/BANKDESK_V4_DESIGN.md.

An episode is one payment request. The bank's records are already in the first message (they are free, so the system
fetches them). The agent then has three kinds of action, one per reply, at most MAX_ACTIONS:

  ACTION: lookup(registry)                       an outside check: registry | number | domain
  ACTION: request_details(purpose="...", reference="...")
                                                 one form per case, at most 5 fields; the key is the fact asked for, the
                                                 value is the wording shown to the customer
  ACTION: decide(risk=high, action=hold, message="...")
                                                 ends the case

Authority stays in code: POLICY lists the actions allowed for each risk level and stake, a payment is refused while a
checked answer contradicts the records, and a form field that asks for a secret ends the case.

The reward is code only. `score_decision` replays a saved state, applies one sampled action, and lets the reference
policy finish the case using only what is in the case file at that point. A form that fails to surface the deciding
fact therefore leads to a worse decision. (The v3 finisher knew the label, so the content of a question never mattered.)

Words: the opening message here is a plain English template built from the structure. Real wording in English, Hindi
and Hinglish comes from GLM, DeepSeek and Adaption in the next step.
"""
import hashlib, json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk_v4 as g

MAX_ACTIONS = 6
RISK = {"low": .05, "medium": .30, "high": .70, "very_high": .95}      # the probability each risk level stands for
BANDS = (("low", 0, .15), ("medium", .15, .50), ("high", .50, .85), ("very_high", .85, 1.0001))
REJECT_COST, SECRET_COST = 0.1, 1.0
RISK_WEIGHT = 0.05     # an honest risk level is worth a little; never enough to justify one more form field (a tap costs 0.03)
SAFE_DEFAULT, SAFE_DEFAULT_COST = "delay", 0.15     # out of turns: delay and hand to a human, scored below a chosen delay
SECRET_WORD = re.compile(r"\b(otp|one[- ]time (password|passcode)|upi pin|mpin|atm pin|pin number|pin|cvv|password|passcode|"
                         r"card number)\b|ओटीपी|पासवर्ड|सीवीवी|पिन", re.I)
ABOUT_OTHERS = re.compile(r"\b(anyone|someone|somebody|anybody|they|he|she|caller|did (he|she|they|anyone|someone)|were you asked|"
                          r"been asked|asked you|asking you|told you)\b|किसी ने|उन्होंने|उसने|कोई", re.I)
NOT_A_SECRET = re.compile(r"\bpin ?code\b|पिन ?कोड", re.I)


def asks_for_secret(label):
    """True if the field asks the customer to give a secret. Asking whether someone else asked for one is fine:
    "Has anyone asked you for an OTP?" is a good question; "Enter the OTP" is not."""
    text = NOT_A_SECRET.sub(" ", label)
    return bool(SECRET_WORD.search(text)) and not ABOUT_OTHERS.search(text)


FIRST = ["Anita", "Ravi", "Meena", "Suresh", "Kavita", "Imran", "Deepa", "Arjun", "Farah", "Gopal", "Lakshmi", "Vikram"]
LAST = ["Sharma", "Iyer", "Khan", "Patel", "Reddy", "Singh", "Das", "Nair", "Joshi", "Menon", "Gupta", "Bose"]
COMPANY = ["Northstar Enterprises", "Greenfield Supplies", "Bluepeak Solutions", "Skyline Services", "Apex Associates",
           "Shree Balaji Agencies", "Unity Ventures", "Harbour Traders", "Crestline Global", "Lotus Infotech",
           "Meridian Logistics", "Sunrise Distributors", "Orchid Retail", "Silverline Systems", "Kaveri Industries",
           "Pinnacle Consultants", "Evergreen Exports", "Aarav Marketing", "Vertex Digital", "Saffron Hospitality"]
# One pool for every story: the name a customer gives must not say whether the story is a scam. (Until 2026-11-16 the
# pool was chosen by story kind, which leaked the label; caught by the wording audit before any training.)
FACTS = {   # the catalogue: fact type -> what the field must ask for, and a default wording
    "purpose": ("what the payment is for", "What is this payment for?"),
    "met_payee": ("whether the customer has met the payee in person", "Have you met this person or visited this business in person?"),
    "reference": ("a reference the bank can check: invoice number, GSTIN, booking or bill number", "Invoice or bill number, and the GSTIN if it is a business"),
    "on_call_now": ("whether someone is on a call with the customer now", "Is someone on a call with you right now, guiding you through this payment?"),
    "told_secret": ("whether the customer was told to keep this from the bank or family", "Has anyone asked you to keep this payment secret?"),
    "bait_explain": ("what the recent small credits from new senders were for", "You received small credits from new senders this week. Are they connected to this payment?"),
    "how_got_details": ("how the customer got the payee's account details", "How did you get this account number?"),
    "who_started": ("whether the customer decided to pay or someone asked them to", "Did you decide to make this payment yourself, or did someone ask you to?"),
}

SYSTEM_PROMPT = """You are the payments desk agent of Horizon Bank. You are an AI. A customer asks for a payment; decide what the bank does.
The bank's records are already in the case file. Read them and the customer's words before you act.
You choose your own steps. Write ONE action per reply, then wait for the bank's answer. At most 6 replies.
  lookup(what)             outside check. what = registry (is the named company registered), number (is the phone number
                           reported), domain (how old is the company's website). Only possible if the customer named one.
  request_details(...)     send the customer a short form of questions. You get ONE form per case, at most 5 fields.
                           List the facts you still need: purpose, met_payee, reference, on_call_now, told_secret,
                           bait_explain, how_got_details, who_started. The bank words each question; to word one
                           yourself write fact="your question". Never ask the customer to give an OTP, PIN, password,
                           CVV or card number.
  decide(risk=..., action=..., message="...")   ends the case. The message goes to the customer in their language.
                           Bank policy: low risk -> pay. medium -> pay or delay. high -> delay or hold. very_high -> hold.
                           No payment while an answer contradicts the records.
Send no form when the records already settle the case. Ask for more when more money is at stake.
Format. Each of these is a separate reply; never write two actions in one reply:
  a reply that checks:   ACTION: lookup(registry)
  a reply that asks:     ACTION: request_details(reference, met_payee, how_got_details)
  a reply that decides:  ACTION: decide(risk=very_high, action=hold, message="We have stopped this payment because ...")"""


# ---------------------------------------------------------------- the bank's policy table, derived from its own costs
def _policy():
    table = {}
    for stake_name, stake in g.STAKE.items():
        for band, lo, hi in BANDS:
            best = set()
            for i in range(41):
                p = lo + (min(hi, 1.0) - lo) * i / 40
                eu = {a: p * g.utility(a, True, stake) + (1 - p) * g.utility(a, False, stake) for a in g.ACTIONS}
                best.add(max(eu, key=eu.get))
            table[(band, stake_name)] = tuple(a for a in g.ACTIONS if a in best)
    return table


POLICY = _policy()      # (risk level, stake) -> actions the agent may take


def lookup_possible(ctx, what):
    return ctx["names_number" if what == "number" else "names_company"] == "yes"


def band_of(p): return next(b for b, lo, hi in BANDS if lo <= p < hi)


# ---------------------------------------------------------------- a case: a world with names, amounts and an opening
BENIGN = ["It is a regular payment I need to make.", "It is for something I have arranged.", "It is a payment I owe.",
          "It is for some work that was done.", "It is for an order.", "It is a family matter.", "It is for a booking."]
RISKY = ["I was told I must pay this today or I will lose everything.", "They said this fee releases the money owed to me.",
         "I was told to move my money now to keep it safe.", "They said I will be in trouble if this is not paid in an hour."]
# Template reasons are chosen by the opening's category only, never by the hidden story.


def case_facts(world):
    """Names, numbers and amounts of a world. The wording step must use exactly these."""
    rnd = random.Random(int(hashlib.sha256(("case" + str(world["id"])).encode()).hexdigest()[:12], 16))
    rec, cues = world["records"], world["cues"]
    savings = rnd.randint(4, 90) * 10_000
    amount = max(500, round(savings * g.STAKE[rec["stake"]] * rnd.uniform(.8, 1.1) / 500) * 500)
    business = rec["payee_type"] == "business"
    company = rnd.choice(COMPANY) if cues["names_company"] == "yes" else None
    payee = (company if business and company else f"{rnd.choice(FIRST)} {rnd.choice(LAST)}" + (" Traders" if business else ""))
    return {"id": world["id"], "holder": f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", "payee": payee,
            "account": str(rnd.randint(10**9, 10**10 - 1)), "amount": amount, "savings": savings, "company": company,
            "phone": f"{rnd.randint(70000, 99999)}{rnd.randint(10000, 99999)}" if cues["names_number"] == "yes" else None}


def template_opening(world, f):
    """Plain English opening built from the structure. Used until real wording exists for a world."""
    rnd = random.Random(int(hashlib.sha256(("open" + str(world["id"])).encode()).hexdigest()[:12], 16))
    opening = f"Please send Rs {f['amount']:,} to {f['payee']}, account {f['account']}."
    cue = world["cues"]["opening"]
    if cue != "bare": opening += " " + rnd.choice(BENIGN if cue == "benign_reason" else RISKY)
    if f["company"] and f["company"] not in opening: opening += f" It is for {f['company']}."
    if f["phone"]: opening += f" They contacted me from {f['phone']}."
    return opening


def make_case(world, words=None):
    """`words`: {"lang", "opening", "answers": {field: customer's text}} written by a model for this world, or None."""
    f = case_facts(world)
    assert not words or words.get("id", world["id"]) == world["id"], "wording row belongs to another world"
    if words: return f | {"opening": words["opening"], "lang": words["lang"], "answer_text": words.get("answers", {})}
    return f | {"opening": template_opening(world, f), "lang": "en", "answer_text": {}}


def first_observation(world, case=None):
    case = case or make_case(world); r = world["records"]
    session = {"none": "no call", "saved": "on a call with a saved contact", "unsaved_long": "on a long call with an unsaved number"}[r["call"]]
    return (f"Customer ({case['holder']}): {case['opening']}\n"
            f"[Case file] pay Rs {case['amount']:,} to {case['payee']}; that is a {r['stake']} share of the customer's savings\n"
            f"[Records] paid this account before: {r['paid_before']} | payee account: {r['payee_age']}, {r['payee_type']} | "
            f"senders to it today: {r['senders_today']} | money leaves it within minutes: {r['fast_withdrawal']} | "
            f"reported by other customers: {r['reports']} | amount against this customer's usual: {r['amount']} | "
            f"limit raised or FD broken in the last two days: {r['recent_change']} | small credits from new senders this week: {r['bait_credits']} | "
            f"session: {session}, screen sharing {r['screen_share']}, new device {r['new_device']} | held by us in the last week: {r['past_hold']}")


# ---------------------------------------------------------------- parsing one reply
ACTION_RE = re.compile(r"ACTION[\s*_`]*:[\s*_`]*([A-Za-z_]+)\s*\(", re.S)
KV_RE = re.compile(r"""(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^,()]+)""", re.S)
OBS = re.compile(r"\n\s*(Customer|Bank|\[Check\]|\[Form\]|\[Policy\]|\[Error\]|\[Case file\]|\[Records\])")


def _split_args(raw):
    """Split on commas that are outside quotes."""
    out, cur, quote = [], "", None
    for ch in raw:
        if quote: cur += ch; quote = None if ch == quote else quote
        elif ch in "\"'": cur += ch; quote = ch
        elif ch == ",": out.append(cur); cur = ""
        else: cur += ch
    return [x.strip() for x in out + [cur] if x.strip()]


def parse(text):
    """-> (tool, args, error). The first ACTION in a reply is the action; anything after it is ignored, as it would be
    behind a stop sequence. Anything after an imagined bank reply is cut off too."""
    text = (text or "").strip()
    cut = OBS.search(text)
    if cut: text = text[:cut.start()]
    hits = list(ACTION_RE.finditer(text))
    if not hits: return None, {}, "write one line: ACTION: tool(...)"
    tool = hits[0].group(1).lower(); raw = text[hits[0].end():hits[1].start() if len(hits) > 1 else len(text)]
    raw = raw[:raw.rfind(")")] if ")" in raw else raw        # a message cut by the token limit still counts
    if tool not in ("lookup", "request_details", "decide"): return None, {}, f"unknown tool {tool}"
    if tool == "request_details":       # fact names, each with optional wording: purpose, reference="Invoice number?"
        args = {}
        for part in _split_args(raw):
            k, eq, v = part.partition("=")
            args[k.strip().strip("'\"").lower()] = v.strip().strip("'\"").strip() if eq else ""
        return tool, args, None
    args = {k.lower(): v.strip().strip("'\"").strip() for k, v in KV_RE.findall(raw)}
    if tool == "lookup":       # lookup(registry), lookup(what=registry) and lookup(number="98...") all mean the same check
        named = [k for k in args if k in g.LOOKUPS]
        args = {"what": named[0]} if named else args if "what" in args else {"what": raw.strip().strip("'\"").lower()}
    if tool == "decide" and ("risk" not in args or "action" not in args):       # decide(very_high, hold, message="...")
        head = [x.strip().strip("'\"").lower() for x in re.split(r"message\s*=", raw)[0].split(",")[:3]]
        for x in head:
            if x.replace(" ", "_") in RISK: args.setdefault("risk", x)
            elif x in g.ACTIONS: args.setdefault("action", x)
    return tool, args, None


# ---------------------------------------------------------------- the episode
class Episode:
    def __init__(self, world, p_scam=0.5, words=None):
        self.world, self.case, self.p_scam = world, make_case(world, words), p_scam
        self.ctx = g.context(world)
        self.lookups, self.fields, self.labels, self.answers = {}, None, {}, {}
        self.log, self.done, self.end = [], False, None
        self.risk = self.action = self.message = None
        self.secret_asked = self.defaulted = False

    def observation0(self): return first_observation(self.world, self.case)

    def contradicted(self):
        """Checked answers that disagree with the records. Payment is refused while any stands."""
        out = []
        if self.answers.get("reference") == "failed": out.append("reference")
        if self.answers.get("on_call_now") == "no" and self.world["records"]["call"] != "none": out.append("on_call_now")
        return out

    def allowed(self, risk):
        acts = POLICY[(risk, self.world["records"]["stake"])]
        if self.contradicted(): acts = tuple(a for a in acts if a != "pay") or ("delay", "hold")
        return acts

    def step(self, text):
        assert not self.done
        tool, args, err = parse(text)
        rec = {"raw": text, "tool": tool, "args": args, "ok": False, "obs": ""}
        if err is None: err = getattr(self, "_" + tool)(args, rec)
        if err: rec["error"] = err; rec["obs"] = f"[Error] {err}. Nothing was done."
        self.log.append(rec)
        if not self.done and len(self.log) >= MAX_ACTIONS:      # out of turns: the bank delays and hands the case to a human
            self.done, self.end, self.action, self.defaulted = True, "max_actions", SAFE_DEFAULT, True
        if rec["obs"] and not self.done: rec["obs"] += f" (actions left: {MAX_ACTIONS - len(self.log)})"
        return "" if self.done else rec["obs"]

    def _lookup(self, args, rec):
        what = (args.get("what") or "").lower()
        if what not in g.LOOKUPS: return "lookup needs one of: registry, number, domain"
        if what in self.lookups: return f"{what} was already checked"
        if not lookup_possible(self.ctx, what): return f"the customer named no {'phone number' if what == 'number' else 'company'}, so there is nothing to look up"
        self.lookups[what] = v = self.world["lookups"][what]; rec["ok"] = True
        rec["obs"] = f"[Check] {what}: " + (v.replace("_", " ") if v != "na" else "no record found")

    def _request_details(self, args, rec):
        if self.fields is not None: return "the form was already sent; one form per case"
        if not args: return "the form needs at least one fact, for example request_details(purpose, reference)"
        bad = [k for k in args if k not in g.FIELDS]
        if bad: return f"unknown fact(s): {', '.join(bad)}"
        if len(args) > g.MAX_FIELDS: return f"at most {g.MAX_FIELDS} fields"
        if any(asks_for_secret(v) for v in args.values()):
            self.secret_asked = True; self.done, self.end = True, "asked_for_a_secret"; rec["ok"] = True; self.fields = []
            rec["obs"] = "[Policy] a form field asked for a secret. The case is closed and logged."; return None
        self.fields, self.labels = list(args), {f: v for f, v in args.items() if v}      # no wording given: the bank's standard question
        self.answers = {f: self.world["answers"][f] for f in self.fields}; bad = self.contradicted(); rec["ok"] = True
        check = {"verified": "checked against the registry", "failed": "does not match any record", "none": "none given", "na": "not applicable"}
        text = self.case["answer_text"]; parts = []
        for f, a in self.answers.items():
            said = f'"{text[f]}"' if text.get(f) else None
            if f == "reference": shown = (said + " -> " if said else "") + check[a]       # the bank checks a reference itself
            else: shown = said or check.get(a, a.replace("_", " "))
            parts.append(f"{f}: {shown}" + (" (CONTRADICTS the records)" if f in bad else ""))
        rec["obs"] = "[Form] " + " | ".join(parts)

    def _decide(self, args, rec):
        risk, action = (args.get("risk") or "").lower().replace(" ", "_"), (args.get("action") or "").lower()
        if risk not in RISK: return "risk must be low, medium, high or very_high"
        if action not in g.ACTIONS: return "action must be pay, delay or hold"
        if action not in self.allowed(risk):
            why = "an answer contradicts the records" if self.contradicted() and action == "pay" else f"at {risk} risk and a {self.world['records']['stake']} stake"
            return f"[Policy] {action} is not allowed ({why}); allowed: {', '.join(self.allowed(risk))}"
        self.risk, self.action, self.message = risk, action, args.get("message", ""); rec["ok"] = True
        self.done, self.end = True, "decided"

    # ------------------------------------------------------------ scoring, code only
    def weights(self): return g.weights(self.ctx, self.lookups, self.answers, self.p_scam)

    def outcome(self):
        """The reward is the expected value of what the agent did, under the exact posterior given what it gathered.
        The same mean as scoring against the hidden truth, without the luck of which story was drawn. Outcomes against
        the truth are kept next to it for reporting."""
        scam = self.world["story"]["truth"] == "scam"; fields = self.fields or []; w = self.weights(); p = g.p_scam_given(w)
        stake = g.STAKE[self.world["records"]["stake"]]
        rejected = sum(not r["ok"] for r in self.log)
        fixed = -g.LOOKUP_COST * len(self.lookups) - REJECT_COST * rejected
        act = self.action if self.action and not self.secret_asked else SAFE_DEFAULT      # also what an unfinished case would get
        expected = decide_value(w, stake, fields, act) + (risk_term(self.risk, p) if self.risk else -RISK_WEIGHT * 0.25)
        truth_u = g.realised(self.world, list(self.lookups), fields, act)
        penalty = (SECRET_COST if self.secret_asked else 0) + (SAFE_DEFAULT_COST if self.defaulted else 0)
        return {"reward": expected + fixed - penalty, "utility": truth_u - penalty, "rejected": rejected, "secret_asked": self.secret_asked,
                "defaulted": self.defaulted, "end": self.end, "action": act, "risk": self.risk, "p_scam_at_decision": p,
                "scam_paid": (act == "pay") if scam else None, "genuine_paid": (act == "pay") if not scam else None,
                "genuine_held": (act == "hold") if not scam else None, "form_sent": self.fields is not None,
                "n_fields": len(fields), "n_lookups": len(self.lookups), "contradicted": self.contradicted()}

    def record(self):
        st = self.world["story"]
        return {"id": self.world["id"], "truth": st["truth"], "kind": st["kind"], "coaching": st["coaching"], "lang": self.case["lang"],
                "turns": [{k: r[k] for k in ("raw", "tool", "args", "ok", "obs")} for r in self.log], "labels": self.labels, **self.outcome()}


def messages(ep, system=SYSTEM_PROMPT):
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": ep.observation0()}]
    for r in ep.log:
        msgs.append({"role": "assistant", "content": r["raw"]})
        if r["obs"]: msgs.append({"role": "user", "content": r["obs"]})
    return msgs


# ---------------------------------------------------------------- exact values of actions
import itertools
import numpy as np

FORMS = [list(c) for k in range(1, g.MAX_FIELDS + 1) for c in itertools.combinations(g.FIELDS, k)]
_V = {}


def risk_term(risk, p):
    """Expected score of a stated risk level when the true chance of a scam is p (a Brier score, so honesty pays)."""
    return -RISK_WEIGHT * (p * (RISK[risk] - 1) ** 2 + (1 - p) * RISK[risk] ** 2)


def _pairs(stake_name, contradicted):
    """(risk, action) pairs the bank's policy allows."""
    out = []
    for r in RISK:
        acts = POLICY[(r, stake_name)]
        if contradicted: acts = tuple(a for a in acts if a != "pay") or ("delay", "hold")
        out += [(r, a) for a in acts]
    return out


def decide_value(w, stake, fields, action):
    """Expected utility of a final action, with the friction of the form already sent falling on genuine customers."""
    u = g._u_matrix(stake, cost=sum(g.FIELDS[f][2] for f in fields), q=g.abandon(len(fields)))
    return float(u[g.ACTIONS.index(action)] @ w / w.sum())


def best_decision(w, stake_name, fields, contradicted):
    """Best allowed (risk, action) now. Returns (value, risk, action)."""
    p = g.p_scam_given(w); stake = g.STAKE[stake_name]
    return max((decide_value(w, stake, fields, a) + risk_term(r, p), r, a) for r, a in _pairs(stake_name, contradicted))


def form_q(w, fields, ctx):
    """Expected value of sending this form, then taking the best allowed decision for each possible set of answers.
    Answers that would contradict the records (a failed reference; "no call" while the session shows one) block payment."""
    stake_name = ctx["stake"]; stake = g.STAKE[stake_name]; L = len(g.STORIES)
    joint = w / w.sum(); shape = []
    for f in fields:
        m = g.lik(g.FIELDS, f, ctx); shape.append(m.shape[1])
        joint = joint[..., None] * m.reshape((L,) + (1,) * (joint.ndim - 1) + (-1,))
    u = g._u_matrix(stake, cost=sum(g.FIELDS[f][2] for f in fields), q=g.abandon(len(fields)))
    eu = np.tensordot(u, joint, axes=(1, 0))                                   # [action, answers...]
    mass = joint.sum(axis=0); scam = joint[g.IS_SCAM].sum(axis=0)              # per answer vector
    bad = np.zeros(shape, dtype=bool)
    for i, f in enumerate(fields):
        idx = [slice(None)] * len(fields)
        if f == "reference": idx[i] = g.FIELDS[f][0].index("failed"); bad[tuple(idx)] = True
        if f == "on_call_now" and ctx["call"] != "none": idx[i] = g.FIELDS[f][0].index("no"); bad[tuple(idx)] = True
    best = np.full(shape, -np.inf)
    for flag in (False, True):
        cand = np.full(shape, -np.inf)
        for r, a in _pairs(stake_name, flag):
            rt = -RISK_WEIGHT * (scam * (RISK[r] - 1) ** 2 + (mass - scam) * RISK[r] ** 2)
            cand = np.maximum(cand, eu[g.ACTIONS.index(a)] + rt)
        best = np.where(bad == flag, cand, best)
    return float(best.sum())


def best_form_q(w, ctx):
    """Best form: exact over every form of up to 3 fields, then grown one field at a time up to the limit."""
    v, f = max((form_q(w, f, ctx), f) for f in FORMS if len(f) <= 3)
    while len(f) < g.MAX_FIELDS:
        v2, f2 = max((form_q(w, f + [x], ctx), f + [x]) for x in g.FIELDS if x not in f)
        if v2 <= v + 1e-9: break
        v, f = v2, f2
    return v, f


def state_value(ctx, lookups, p_scam=0.5):
    """Value of a case before any form is sent, playing the best of: decide now, the best form, or one more lookup.
    Exact over lookup outcomes and form answers. Returns (value, kind, detail). Cached per state."""
    key = (tuple(sorted(ctx.items())), tuple(sorted(lookups.items())), p_scam, g.params_hash())
    if key in _V: return _V[key]
    w = g.weights(ctx, lookups, None, p_scam)
    v, r, a = best_decision(w, ctx["stake"], [], False); best = (v, "decide", (r, a))
    fv, ff = best_form_q(w, ctx)
    if fv > best[0] + 1e-9: best = (fv, "form", ff)
    for name in g.LOOKUPS:
        if name in lookups or not lookup_possible(ctx, name): continue
        lv = lookup_q(ctx, lookups, name, p_scam)
        if lv > best[0] + 1e-9: best = (lv, "lookup", name)
    _V[key] = best
    return best


def lookup_q(ctx, lookups, name, p_scam=0.5):
    """Expected value of buying one lookup and then playing on."""
    w = g.weights(ctx, lookups, None, p_scam); m = g.lik(g.LOOKUPS, name, ctx); pv = (w[:, None] * m).sum(axis=0) / w.sum()
    return sum(pv[i] * state_value(ctx, lookups | {name: v}, p_scam)[0] for i, v in enumerate(g.LOOKUPS[name][0]) if pv[i] > 1e-12) - g.LOOKUP_COST


def render_form(fields, labels=None):
    """Bare fact names (the bank words the questions), or fact="wording" for the facts that have a label."""
    return "ACTION: request_details(" + ", ".join(f'{f}="{labels[f]}"' if labels and labels.get(f) else f for f in fields) + ")"


def candidates(ep):
    """Every sensible action from here with its exact value: [(value, kind, detail, action text)]. Lookup costs already
    paid and rejected actions are the same for all of them, so they are left out."""
    w = ep.weights(); ctx = ep.ctx; stake_name = ctx["stake"]; fields = ep.fields or []; p = g.p_scam_given(w); out = []
    for r, a in _pairs(stake_name, bool(ep.contradicted())):
        out.append((decide_value(w, g.STAKE[stake_name], fields, a) + risk_term(r, p), "decide", (r, a),
                    f'ACTION: decide(risk={r}, action={a}, message="")'))
    if ep.fields is None and len(ep.log) < MAX_ACTIONS - 1:
        out += [(form_q(w, f, ctx), "form", f, render_form(f)) for f in FORMS]
        if len(ep.log) < MAX_ACTIONS - 2:
            out += [(lookup_q(ctx, ep.lookups, n, ep.p_scam), "lookup", n, f"ACTION: lookup({n})") for n in g.LOOKUPS if n not in ep.lookups and lookup_possible(ctx, n)]
    return sorted(out, key=lambda x: -x[0])


def soft_targets(ep, tau=0.02):
    """A distribution over the candidates for training: first the kind of action, then the action within the kind,
    each a softmax of value / tau. Near-tied actions keep weight, so the trained policy is not peaked on one of them."""
    cand = candidates(ep); kinds = {}
    for c in cand: kinds.setdefault(c[1], []).append(c)
    top = {k: v[0][0] for k, v in kinds.items()}; z = max(top.values())
    pk = {k: np.exp((t - z) / tau) for k, t in top.items()}; tot = sum(pk.values()); out = []
    for k, items in kinds.items():
        e = np.exp((np.array([c[0] for c in items]) - items[0][0]) / tau); e /= e.sum()
        out += [(float(pk[k] / tot * e[i]), c) for i, c in enumerate(items)]
    return sorted(out, key=lambda x: -x[0])


# ---------------------------------------------------------------- scripted agents (the reference, and baselines)
def reference_step(ep):
    """The reference policy: the action with the highest exact value from wherever the case stands."""
    return candidates(ep)[0][3]


def run(world, agent, p_scam=0.5, words=None):
    ep = Episode(world, p_scam, words)
    while not ep.done: ep.step(agent(ep))
    return ep


def agent_always(action, risk):
    return lambda ep: f'ACTION: decide(risk={risk}, action={action}, message="")'


def agent_fixed_form(ep):
    if ep.fields is None: return render_form(g.FIXED_FORM)
    return reference_step(ep)


# ---------------------------------------------------------------- reward for one sampled decision (GRPO)
def score_decision(world, prior_actions, sampled, p_scam=0.5, words=None):
    """Replay `prior_actions`, apply `sampled`, and return the exact expected value of the case from there, assuming
    the reference policy plays the rest. No luck from the hidden story or from which answers the customer gave.
    A rejected sample costs REJECT_COST and a turn. Returns (reward, info)."""
    ep = Episode(world, p_scam, words)
    for a in prior_actions:
        if ep.done: break
        ep.step(a)
    before = (dict(ep.lookups), ep.fields)
    if not ep.done: ep.step(sampled)
    last = ep.log[-1]; fixed = -g.LOOKUP_COST * len(before[0]) - REJECT_COST * sum(not r["ok"] for r in ep.log)
    if ep.done:
        o = ep.outcome(); return o["reward"], {"kind": last["tool"], "ok": last["ok"], "end": ep.end}
    if last["ok"] and last["tool"] == "request_details":      # value of the form itself, averaged over what could come back
        ep2 = Episode(world, p_scam, words)
        for a in prior_actions: ep2.step(a)
        v = form_q(ep2.weights(), ep.fields, ep.ctx)
    elif ep.fields is None:                                   # a lookup, or a rejected action: play on from the new state
        v = state_value(ep.ctx, ep.lookups, p_scam)[0]
        if last["ok"] and last["tool"] == "lookup":           # average over what the lookup could have shown
            v = lookup_q(ep.ctx, before[0], last["args"]["what"], p_scam) + g.LOOKUP_COST
            fixed -= g.LOOKUP_COST
    else:                                                     # form already sent: only a decision is left
        v = best_decision(ep.weights(), ep.ctx["stake"], ep.fields, bool(ep.contradicted()))[0]
    return v + fixed, {"kind": last["tool"], "ok": last["ok"], "end": None}


if __name__ == "__main__":
    wid = sys.argv[1] if len(sys.argv) > 1 else "demo-5"
    w = g.sample_world(wid); ep = Episode(w)
    print(json.dumps(w["story"])); print(ep.observation0())
    while not ep.done:
        a = reference_step(ep); obs = ep.step(a); print(a); print(obs) if obs else None
    print(json.dumps(ep.outcome(), indent=1, default=str))
