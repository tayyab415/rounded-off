"""BankDesk v4, step 3: wording. Code picks the facts, a model writes the customer's words, code and a second model
check that the words carry exactly the structure. Design: notes/BANKDESK_V4_DESIGN.md 12.2. Acceptance: RULE V4-3
(every row) and RULE V4-4 (leak audit on train).

For each world: one language (deterministic from the id), one writer (GLM-5.3-Flash for even world indexes,
DeepSeek-V4.1-Flash for odd), one reviewer (the other model). A row is kept only if
  (a) code checks pass: amount, account and payee in the opening; company iff named; phone iff named; no other
      numbers; the code-made reference code iff a reference is given; script matches the language; no empty field;
      no urgency in a bare opening; no story words or stray names beyond what the categories allow; no answer that
      is an exact duplicate of one already kept more than 3 times in the same language and split; and
  (b) the reviewer, shown only the text, reads back the opening class and every form answer's category.
Rows are never edited. Kept rows plug into bankdesk_v4_env.Episode(world, words=row). Each row carries
"world_hash" = bankdesk_v4.params_hash(), so a row cannot silently be used with a changed generator.

  python3 scripts/bankdesk_v4_words.py --prefix train --n 600 --name train [--stop-at 9.22]
  python3 scripts/bankdesk_v4_words.py audit --name train          # RULE V4-4 (--regime shift for words_shift)
  -> data/bankdesk_v4/words_<name>.jsonl (kept), words_<name>.rejected.jsonl (dropped, with reasons; appended)
Resumable and chunked: ids already kept are skipped, so a re-run retries only the dropped rows. --stop-at stops
before a chunk once the Nebius ledger passes that dollar total.

Prompt versions (PROMPT_VERSION is written into every row):
  1  first pilot. Hindi 12/24 and Hinglish 8/14 kept, under the 70% bar.
  2  one fix after the pilot, for the failed rows only: a language reminder at the end of each task; no Latin-script
     typing styles (all lowercase, pls/a/c) for Hindi; the cover reason now matches the purpose category; the
     categories win over the situation line; per-category phrasing (name the relationship, the thing bought, the
     channel); the opening says nothing about form topics; a bare opening has no urgency; a given phone must appear.
  3  the writer no longer sees the hidden story (truth, kind, coaching). Code picks the opening's reason and the
     purpose detail from pools keyed by category only, so the words cannot carry the truth; only a risky_reason
     opening gets a situation to tell. The purpose detail is the opening's reason whenever the two categories are
     compatible; a risky situation is chosen by the purpose category, so the two always agree. Reference codes come from code (unique per world, five formats) and no example code is in the
     prompt. A per-world style seed (age, job, formality, greeting or none, first words, length, typing, answer
     style), and a per-world wording angle for the plain yes/no answers. Answers say who asked only in generic
     words, give no names, places or past events. New code checks: reference code iff given, urgency in a bare or
     benign opening, story words, stray capitalised names (English) or stray Latin words (Hindi), duplicate answers.
     Top-up (same prompt): answers of at most 4 words may repeat 12 times per language and split (longer ones 3);
     a retry gets a fresh style seed, answer angles and pool picks (attempt number in the seed keys), recorded as
     "attempt" in the row. The writer was already at temperature 0.9 for every attempt.
Every call goes through nebius_client.chat(), so the $15 cap and the spend log apply. Content: victim-side and
genuine-customer messages only; the writer never writes a scammer's words or any instructions.
"""
import argparse, hashlib, json, math, os, re, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bankdesk_v4 as g
import bankdesk_v4_env as e

PROMPT_VERSION = 3
GLM, DEEPSEEK = "zai-org/GLM-5.3-Flash", "deepseek-ai/DeepSeek-V4.1-Flash-1017"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bankdesk_v4")
LANGS = (("en", .40), ("hi", .35), ("hinglish", .25))
FIELD_ORDER = list(g.FIELDS)
DUP_LIMIT = 3          # an answer already kept more than this many times (same language, same split) drops the row
SHORT_WORDS, SHORT_LIMIT = 4, 12   # answers of at most 4 words ("No.", "Haan ji") may appear up to 12 times; longer ones 3 (from the top-up on)


def _h(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode()).digest()


# ---------------------------------------------------------------- assignment
def world_index(world_id):
    m = re.search(r"(\d+)$", str(world_id))
    return int(m.group(1)) if m else int(hashlib.sha256(str(world_id).encode()).hexdigest()[:8], 16)


def assign_lang(world_id):
    u = int(hashlib.sha256(("lang" + str(world_id)).encode()).hexdigest()[:12], 16) / 16 ** 12
    acc = 0.0
    for lang, p in LANGS:
        acc += p
        if u < acc: return lang
    return LANGS[-1][0]


def writer_reviewer(world_id):
    return (GLM, DEEPSEEK) if world_index(world_id) % 2 == 0 else (DEEPSEEK, GLM)


# ---------------------------------------------------------------- reference codes, made by code
_ALNUM = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def ref_code(world_id):
    """A reference code unique to the world, in one of five formats. Independent of the story."""
    h = _h("ref", world_id); n = int.from_bytes(h[:8], "big"); kind = h[8] % 5
    d = lambda k, s: str(n // 10 ** s % 10 ** k).zfill(k)
    a = lambda k, s: "".join(_ALNUM[h[9 + s + i] % len(_ALNUM)] for i in range(k))
    if kind == 0: return f"INV-{d(6, 0)}"
    if kind == 1: return f"ORD/{d(4, 5)}/{d(2, 9)}"
    if kind == 2: return f"BL{d(8, 2)}"
    if kind == 3: return f"BK{a(6, 0)}"
    letters = "".join("ABCDEFGHIJKLMNOPQRSTUVWXYZ"[h[12 + i] % 26] for i in range(6))
    return f"{d(2, 0) if d(2, 0) != '00' else '27'}{letters[:5]}{d(4, 3)}{letters[5]}1Z{_ALNUM[h[20] % len(_ALNUM)]}"


def ref_kind(code):
    for pre, kind in (("INV-", "an invoice number"), ("ORD/", "an order number"), ("BL", "a bill number"), ("BK", "a booking reference")):
        if code.startswith(pre): return kind
    return "a GSTIN"


# ---------------------------------------------------------------- what the text must show (the reviewer's categories)
def text_labels(world):
    """The category each piece of text must express. Some structure is invisible in text by design:
    reference verified/failed is decided by the bank's check, and on_call_now na (no call) reads the same as no."""
    a = world["answers"]
    lab = {"opening": world["cues"]["opening"]}
    for f in FIELD_ORDER:
        v = a[f]
        if f == "reference": v = "none" if v == "none" else "gave_reference"
        elif f == "on_call_now": v = "yes" if v == "yes" else "no"
        elif f == "bait_explain": v = "no_credits" if v == "na" else v
        lab[f] = v
    return lab


CATEGORIES = {"opening": ("bare", "benign_reason", "risky_reason"),
              "purpose": ("goods_services", "fee_to_get_something", "known_person", "other"),
              "met_payee": ("yes", "no"), "reference": ("gave_reference", "none"), "on_call_now": ("yes", "no"),
              "told_secret": ("yes", "no"), "bait_explain": ("from_this_work", "unrelated", "no_credits"),
              "how_got_details": ("bill_or_in_person", "chat_message", "phone_call"), "who_started": ("me", "someone_asked")}

QUESTIONS = {   # what the customer is replying to; the agent's own wording will differ, so answers must stand alone
    "purpose": "What is this payment for?",
    "met_payee": "Have you met this person or visited this business in person?",
    "reference": "Invoice or bill number, and the GSTIN if it is a business.",
    "on_call_now": "Is someone on a call with you right now, guiding you through this payment?",
    "told_secret": "Has anyone asked you to keep this payment secret?",
    "bait_explain": "You received small credits from new senders this week. Are they connected to this payment?",
    "how_got_details": "How did you get this account number?",
    "who_started": "Did you decide to make this payment yourself, or did someone ask you to?",
}

# Shared by writer and reviewer, so both read the categories the same way.
DEFINITIONS = """OPENING CLASS (the customer's first message)
- bare: only the request: amount, payee, account, and the company name or a contact number if present. No reason,
  no purpose, no story, no urgency, no "for ...", no "because ...". Naming the company or giving the payee's contact
  number is not a reason.
- benign_reason: the request plus an ordinary reason that would not worry a bank: a bill, an order, rent, a purchase,
  a booking, family, a friend, paying someone back, a personal payment.
- risky_reason: the request plus a reason that should worry a bank, even though the customer tells it innocently and
  believes it: a fee, tax or charge to unlock earnings, profits, a loan, a job or a prize; an officer, police
  or an official threatening arrest, a case or a frozen account; moving money to a "safe" or "secure" account on
  someone's instruction; a relative asking for money urgently from a new number; a buyer who says you must pay to
  receive money; being pressed to pay right now or something bad happens (for example a hospital refusing treatment).

FORM ANSWERS (each is a reply to one question; classify by what the reply says)
- purpose ("What is this payment for?"):
  goods_services = paying for goods or services bought, ordered or used: a product, a bill, a repair, rent, a booking,
    an order, school or hospital fees;
  fee_to_get_something = a fee, deposit, tax or charge that must be paid first in order to get something: a job, a
    loan, a prize, a refund, release of earnings or profits, a verification or clearance;
  known_person = money to a person the customer knows personally: family, a friend, a colleague, paying back a loan;
  other = none of the three: moving one's own money, savings, a deposit into an investment, a donation, or a vague
    answer that fits none of the above.
- met_payee ("Have you met this person or visited this business in person?"): yes / no.
- reference ("Invoice or bill number, and the GSTIN if it is a business"):
  gave_reference = the reply gives a concrete reference: an invoice, bill, order or booking number, or a GSTIN;
  none = the reply says there is no invoice, bill or reference, or gives none.
- on_call_now ("Is someone on a call with you right now, guiding you?"): yes / no.
- told_secret ("Has anyone asked you to keep this payment secret?"): yes / no.
- bait_explain ("You received small credits from new senders this week. Are they connected to this payment?"):
  from_this_work = yes, those credits came from the same work, scheme or people this payment is for;
  unrelated = the customer did get such credits, but they have nothing to do with this payment;
  no_credits = the customer says they did not receive any such credits.
- how_got_details ("How did you get this account number?"):
  bill_or_in_person = from a printed bill or invoice, a passbook, or given in person;
  chat_message = sent by WhatsApp, Telegram, SMS, email or an app chat;
  phone_call = told over a phone call.
- who_started ("Did you decide to make this payment yourself, or did someone ask you to?"):
  me = the customer decided on their own; someone_asked = someone asked or told them to pay."""

WRITER_SYSTEM = """You write test data for a bank's payment-protection agent at Horizon Bank, an Indian bank. Each task
describes one bank customer and one payment they want to make through the bank's chat. You write only what that
customer types: their opening message, and their short replies to a form the bank may send. You write only the
customer's side, in their own words. Never write what anyone else says to the customer, never give instructions of
any kind, and never let the customer call anything a scam, fraud or suspicious.

You are given a STRUCTURE. Your text must carry exactly that structure and nothing more. A reader who sees only your
text must be able to recover every category below, and must learn nothing else: no story, no history, no names, no
places, no dates, no earlier payments, no feelings about the payee beyond what the task gives you.

LANGUAGE
- en: English as an Indian bank customer types it.
- hi: Hindi in Devanagari script. Only names, the company name, numbers and the reference code stay in Latin letters
  and Western digits (0-9). Do not use Devanagari digits. English words that Hindi speakers borrow are written in
  Devanagari too: अकाउंट, कॉल, मैसेज, बिल, इनवॉइस, रेफरेंस, नंबर, ऑर्डर, पेमेंट, कॉन्टैक्ट. No other Latin words.
- hinglish: Hindi written in Latin script, the way people type on WhatsApp. English words may be mixed in, but the
  grammar is Hindi. A plain English sentence is wrong. No Devanagari at all.
Write the opening and every answer in the given language.

FIXED DETAILS (in the opening message)
- The amount in Western digits, in exactly one of these forms: 232500 or 232,500 or 2,32,500 (Rs or a rupee sign
  before it is fine). Never in words, never as "lakh" or "k".
- The account number in digits exactly as given, with no spaces.
- The payee name exactly as given, in Latin letters.
- company: if one is given, write it exactly as given, in Latin letters. If it is "none", do not name any company,
  firm, app, website, brand or platform.
- phone: if one is given, write its 10 digits exactly as given, with no spaces. If it is "none", write no phone
  number.
- No other numbers in the opening: no dates, times, other amounts, counts or percentages.
- No other names of people or places anywhere, in the opening or the answers.

""" + DEFINITIONS + """

HOW TO WRITE THE OPENING
- bare: no reason and no urgency at all (no "urgent", "today", "now", "quickly", "asap", "jaldi", "abhi", "turant",
  "जल्दी", "आज", "अभी"). Just the request. A company or a contact number, if given, is attached to the payee without
  saying why.
- benign_reason: state the given REASON plainly in words. Nothing alarming, no urgency (the same words as for bare
  are not allowed).
- risky_reason: tell the given SITUATION in the customer's believing words, so that a careful bank officer would
  worry. Tell only that situation; add no other events, names or history.
- The opening says nothing about the form topics (meeting the payee, how the account details arrived, who asked,
  calls, secrecy, credits) unless the risky situation itself contains it.
- Follow the STYLE seed: greeting (or none), the first words, the length, formality and typing habits.

HOW TO WRITE THE FORM ANSWERS
- Each answer replies to its own question only and expresses exactly its category, so a reader would put it in that
  category and no other. It adds nothing else: no names, no places, no events, no reasons, no story.
- purpose: describe the payment with the given PURPOSE DETAIL, in the plain words of its category. When the opening
  gives a reason, the purpose answer describes that same payment.
- reference: if a code is given, the reply gives exactly that code, written as given. If none, the reply says there
  is no bill, invoice or reference, with no code or number.
- who_started someone_asked: say someone asked or told them to pay, in generic words ("they asked me", "I was told
  to"); never say who.
- how_got_details: name only the channel (a printed bill or slip, or handed over in person; WhatsApp, SMS, email or
  chat; a phone call).
- bait_explain from_this_work: the credits came from the same people or work this payment is for, in generic words.
- Vary the wording. Simple yes/no replies are where everyone sounds the same: for "nobody is on a call", "no such
  credits" and "nobody asked me to keep it secret", follow the angle given in brackets and find this customer's own
  way to say it, in the ANSWER STYLE.

OUTPUT
Reply with one JSON object only, no markdown fences, no commentary:
{"opening": "...", "answers": {"purpose": "...", "met_payee": "...", "reference": "...", "on_call_now": "...",
"told_secret": "...", "bait_explain": "...", "how_got_details": "...", "who_started": "..."}}
Every value is a non-empty string in the given language."""

REVIEW_SYSTEM = """You check customer messages written for a bank's test set. For each item you see only text: a
customer's opening message to the bank's payment chat, and the customer's replies to form questions. You do not know
anything else about the customer. Read each reply on its own and classify it by what it actually says, using the
definitions below. Do not guess what a cautious bank would think the hidden truth is; classify only the literal
content. Languages: English, Hindi (Devanagari) and Hinglish (Hindi in Latin script).

""" + DEFINITIONS + """

OUTPUT
For every item, give one category for "opening" and one for each of the eight fields, using exactly the category
names above (for example "benign_reason", "fee_to_get_something", "gave_reference", "no_credits", "someone_asked").
Reply with ONLY one JSON object mapping item number to an object, for example:
{"1": {"opening": "bare", "purpose": "goods_services", "met_payee": "yes", "reference": "none", "on_call_now": "no",
"told_secret": "no", "bait_explain": "no_credits", "how_got_details": "chat_message", "who_started": "me"}}
No markdown fences, no commentary."""

# ---------------------------------------------------------------- what the writer is told (v3: never the hidden story)
PURPOSE_POOL = {   # chosen by the purpose category only, never by the story
    "goods_services": ["an order they placed", "a bill for repair work at home", "something they are buying", "this month's rent",
                       "school fees", "a furniture purchase", "a service they used", "a booking they made"],
    "known_person": ["money for a family member", "paying back a friend", "a gift for a relative", "helping a cousin with expenses",
                     "money for their sister", "returning money a colleague lent them"],
    "other": ["moving their own savings", "a transfer of their own money", "a deposit into an investment", "a donation"],
    "fee_to_get_something": ["a processing fee to release a refund", "a registration fee before starting a job",
                             "a charge to get a loan approved", "a tax to release their earnings", "a fee to claim a prize",
                             "a verification charge"],
}
BENIGN_FOR_FEE = ["a personal payment", "money for a family member"]    # benign opening while the form says fee
RISKY = {   # situations a risky_reason opening can tell, in the customer's believing view
    "task_job": "they did paid online tasks and now have to pay a charge before their earnings can be withdrawn",
    "digital_arrest": "an officer told them their name is in a case and they must pay for verification or be arrested",
    "investment": "their online trading profits are shown in the app, and they must pay a tax or fee to withdraw them",
    "fake_company": "a company offering them a job or dealership needs a registration or security fee first",
    "safe_account": "someone from the bank's security side told them to move their money to a safe account",
    "relative_emergency": "a relative messaged from a new number and needs the money urgently",
    "marketplace": "a buyer for something they are selling says they must pay first to receive the buyer's money",
    "medical_urgent": "the hospital will not start treatment until this is paid",
    "routine_payee": "the payee says services will be cut off unless it is paid at once",
    "new_vendor": "the supplier insists on immediate payment to this new account or the order is cancelled",
    "new_individual": "a friend needs the money at once for an emergency",
    "big_purchase": "the seller says the deal is lost unless the token amount is paid right away",
}
# The situation is chosen by the purpose category (part of the structure), never by the hidden story, and the
# purpose answer then describes the same thing. (v3 first draft chose it by story kind, which leaked the truth.)
RISKY_BY_PURPOSE = {"goods_services": ["medical_urgent", "routine_payee", "new_vendor", "big_purchase"],
                    "known_person": ["relative_emergency", "new_individual"],
                    "fee_to_get_something": ["task_job", "investment", "fake_company", "marketplace"],
                    "other": ["digital_arrest", "safe_account"]}

AGES = ["22", "27", "31", "36", "42", "48", "55", "61", "67", "74"]
JOBS = ["college student", "software engineer", "shopkeeper", "retired teacher", "nurse", "homemaker", "taxi driver",
        "small factory owner", "government clerk", "pharmacist", "farmer", "sales executive", "retired army officer",
        "beautician", "accountant", "school principal"]
FORMALITY = ["formal", "neutral", "casual"]
STYLES = ["careful full sentences and punctuation", "all lowercase, few commas", "short abbreviations like pls, a/c, amt",
          "polite, uses sir/madam or ji", "chatty and warm", "terse, almost telegraphic", "run-on sentences joined with commas"]
STYLES_HI = [s for s in STYLES if "lowercase" not in s and "a/c" not in s] + ["few commas, no full stops", "short and clipped"]
GREETINGS = {"en": ["Hi", "Hello", "Good morning", "Dear sir/madam", "Hey", "Good evening"],
             "hi": ["नमस्ते", "नमस्कार", "प्रणाम", "सुनिए", "हैलो"],
             "hinglish": ["Namaste", "Hello ji", "Hi", "Sir", "Pranam", "Suniye"]}
STARTS = ["the amount", "the payee's name", "a question to the bank", "what they need (I need / mujhe / मुझे)",
          "the payee's account number (it is the account they pay into)", "a word about the app or the bank chat"]
ANGLES = {   # per-world angle for the plain answers that otherwise come out word for word the same
    ("on_call_now", "no"): ["say they are alone", "say the phone is not in use", "say they are doing it by themselves",
                            "a short denial", "say no one is guiding them", "say there is no call going on"],
    ("on_call_now", "yes"): ["say someone is on the line", "say they are talking to someone now", "a short yes",
                             "say yes, someone is helping on the phone"],
    ("told_secret", "no"): ["say nobody said anything like that", "say there is nothing to hide", "a short no",
                            "say no one asked them to hide it", "say their family can know"],
    ("told_secret", "yes"): ["say they were told not to tell anyone", "say they were asked to keep it quiet", "a short yes"],
    ("bait_explain", "no_credits"): ["say no such money came", "say they have not seen any such credits",
                                     "a short denial", "say nothing like that arrived in the account"],
    ("who_started", "me"): ["say it was their own decision", "say no one asked them", "say they chose to pay",
                            "a short reply", "say it is their own idea"],
    ("who_started", "someone_asked"): ["say they were asked to", "say they were told to pay", "a short reply",
                                       "say the request came from the other side"],
    ("reference", "none"): ["say there is no bill", "say they were not given any invoice", "a short reply",
                            "say there is no number to give"],
    ("met_payee", "yes"): ["a short yes", "say they have met", "say yes, in person"],
    ("met_payee", "no"): ["a short no", "say they have not met", "say never in person"],
}
LENGTHS = ["one short line", "two sentences", "three sentences"]
ANSWER_STYLES = ["very short replies of three to six words", "one plain sentence each", "polite replies with ji or sir",
                 "replies that echo part of the question", "casual replies", "mixed lengths, some short, some a full sentence",
                 "replies that start with yes or no and then add a few words"]
LANG_REMINDER = {
    "en": "Remember: everything (opening and all eight answers) in English.",
    "hi": "Remember: everything (opening and all eight answers) in Hindi in Devanagari script. Latin letters only for the "
          "payee, company and the reference code; borrowed English words in Devanagari (अकाउंट, कॉल, ऑर्डर, पेमेंट).",
    "hinglish": "Remember: everything (opening and all eight answers) in Hinglish: Hindi sentences written in Latin letters. "
                "A plain English sentence is wrong; no Devanagari.",
}


def style_seed(world_id, lang="en", attempt=0):
    """Per-world style, chosen by code, independent of the story. A retry (attempt >= 1) gets a fresh seed."""
    h = _h("style", world_id) if not attempt else _h("style", world_id, f"retry{attempt}")
    pick = lambda lst, i: lst[h[i] % len(lst)]
    greet = None if h[5] % 3 == 0 else pick(GREETINGS[lang], 6)
    start = pick(STARTS, 7)
    return {"age": pick(AGES, 0), "job": pick(JOBS, 1), "formality": pick(FORMALITY, 2),
            "typing": pick(STYLES_HI if lang == "hi" else STYLES, 3), "length": pick(LENGTHS, 4),
            "greeting": greet, "start": start if not greet else f"the greeting, then {start}", "answers": pick(ANSWER_STYLES, 8)}


def plan(world, attempt=0):
    """What the writer is told about the content: the opening's reason or situation, and the purpose detail."""
    lab = text_labels(world); op, pur = lab["opening"], lab["purpose"]
    h = _h("plan", world["id"]) if not attempt else _h("plan", world["id"], f"retry{attempt}")
    reason = situation = None
    if op == "benign_reason":
        pool = BENIGN_FOR_FEE if pur == "fee_to_get_something" else PURPOSE_POOL[pur]
        reason = pool[h[0] % len(pool)]
    if op == "risky_reason":
        opts = RISKY_BY_PURPOSE[pur]; situation = RISKY[opts[h[2] % len(opts)]]
    if op == "benign_reason" and pur != "fee_to_get_something": detail = reason
    elif op == "risky_reason": detail = "the same thing the opening's situation describes"
    else: detail = PURPOSE_POOL[pur][h[1] % len(PURPOSE_POOL[pur])]
    return {"reason": reason, "situation": situation, "purpose_detail": detail}


def writer_task(world, facts, lang, attempt=0):
    lab = text_labels(world); s = style_seed(world["id"], lang, attempt); p = plan(world, attempt)
    lines = [f"LANGUAGE: {lang}",
             f"STYLE: {facts['holder']}, age {s['age']}, {s['job']}; {s['formality']}; typing: {s['typing']}; "
             f"greeting: {s['greeting'] or 'none'}; start the opening with {s['start']}; opening length: {s['length']}.",
             f"ANSWER STYLE: {s['answers']}.",
             f"amount: {facts['amount']}", f"account: {facts['account']}", f"payee: {facts['payee']}",
             f"company: {facts['company'] or 'none'}", f"phone: {facts['phone'] or 'none'}",
             f"OPENING CLASS: {lab['opening']}"]
    if p["reason"]: lines.append(f"REASON: {p['reason']}")
    if p["situation"]: lines.append(f"SITUATION: {p['situation']}")
    lines.append("FORM ANSWERS:")
    for f in FIELD_ORDER:
        v = lab[f]
        if f == "purpose": v += f" (purpose detail: {p['purpose_detail']})"
        if f == "reference" and v == "gave_reference": c = ref_code(world["id"]); v += f" (code: {c}, {ref_kind(c)})"
        ang = ANGLES.get((f, v))
        if ang: v += f" ({ang[(_h('angle', world['id'], f) if not attempt else _h('angle', world['id'], f, f'retry{attempt}'))[0] % len(ang)]})"
        lines.append(f"- {f}: {v}")
    lines += [LANG_REMINDER[lang], "Write the JSON now."]
    return "\n".join(lines)


# ---------------------------------------------------------------- parsing
def parse_json(text):
    """The first complete JSON object in a reply, or None. Tolerates fences, think blocks and trailing commas."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': in_str = False
            elif c == '"': in_str = True
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    blob = text[start:i + 1]
                    for cand in (blob, re.sub(r",\s*([}\]])", r"\1", blob)):
                        try: return json.loads(cand)
                        except json.JSONDecodeError: pass
                    break
        start = text.find("{", start + 1)
    return None


# ---------------------------------------------------------------- code checks (no model)
DEVA = re.compile(r"[ऀ-ॿ]")
DEVA_LETTER = re.compile(r"[ऀ-ॣॱ-ॿ]")
DEVA_DIGIT = re.compile(r"[०-९]")
LATIN = re.compile(r"[A-Za-z]")
HINGLISH_WORDS = {"hai", "hain", "ka", "ki", "ke", "ko", "se", "mein", "mujhe", "maine", "mera", "meri", "mere", "nahi",
                  "nahin", "nhi", "kar", "karna", "karo", "kijiye", "karein", "krna", "haan", "ji", "bhej", "bhejna",
                  "bhejo", "bhejiye", "paise", "aur", "yeh", "woh", "wo", "tha", "thi", "hoon", "hu", "hun", "kya", "liye",
                  "kiya", "diya", "raha", "rahi", "rahe", "abhi", "koi", "kuch", "bhai", "bhi", "toh", "to", "hua", "lekin"}
COMPANY_WORDS = re.compile(r"\b(pvt|ltd|limited|llp|inc|solutions|technologies|enterprises|www\.|\.com|\.in)\b", re.I)
ALL_COMPANIES = sorted({c for v in e.COMPANY.values() for c in v} if isinstance(e.COMPANY, dict) else set(e.COMPANY),
                       key=len, reverse=True)
URGENT = re.compile(r"\b(urgent|urgently|asap|immediately|quick|quickly|fast|today|right away|now|jaldi|jldi|abhi|turant|"
                    r"aaj|fatafat)\b|जल्दी|अभी|आज|तुरंत|फ़ौरन|फौरन", re.I)
STORY = re.compile(   # words that tell the hidden story; allowed only where the category itself says it
    r"\b(tasks?|earnings?|earned|profits?|trading|arrest\w*|police|officer|cbi|customs|safe account|secure account|prize|"
    r"lottery|unlock\w*|withdraw\w*|kamai|munafa|giraftar\w*|inaam|nephew|niece|bhatija|bhanja|hospital|treatment|"
    r"scheme|returns|commission)\b|टास्क|कमाई|मुनाफ|प्रॉफिट|ट्रेडिंग|गिरफ्त|पुलिस|अफसर|अधिकारी|सेफ अकाउंट|"
    r"सुरक्षित खात|इनाम|लॉटरी|भतीज|भांज|अस्पताल|इलाज|कमीशन", re.I)
NAME_OK = {"i", "whatsapp", "sms", "upi", "gstin", "gst", "telegram", "sir", "madam", "ma'am", "maam", "ji", "ok", "okay",
           "rs", "inr", "neft", "imps", "rtgs", "horizon", "bank", "email", "e-mail", "gmail", "instagram", "facebook", "app",
           "pls", "please", "thanks", "chat", "online", "paper", "slip", "receipt", "invoice", "bill", "thank", "hello", "hi", "namaste", "dear", "kindly", "gpay", "paytm", "phonepe", "pdf",
           "a/c", "ac", "no", "yes", "id", "otp", "pin", "q", "hey", "pranam", "suniye", "haan", "nahi", "bhai"}


def indian_commas(n):
    s = str(n)
    if len(s) <= 3: return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2: groups.insert(0, head[-2:]); head = head[:-2]
    if head: groups.insert(0, head)
    return ",".join(groups + [tail])


def amount_forms(n):
    return sorted({str(n), f"{n:,}", indian_commas(n)}, key=len, reverse=True)


def has_amount(text, n):
    return any(re.search(r"(?<![\d,.])" + re.escape(f) + r"(?!\d|[,.]\d)", text) for f in amount_forms(n))


def _join_digits(text):
    """Digits split by a space or hyphen ("98765 43210") are read as one number."""
    return re.sub(r"(?<=\d)[ \-](?=\d)", "", text)


def _strip(text, words):
    for w in words:
        if w: text = re.sub(re.escape(w), " ", text, flags=re.I)
    return text


def script_share(text, facts):
    """Share of Devanagari among letters, ignoring the fixed Latin names and any token that contains a digit."""
    t = _strip(text, [facts["payee"], facts["company"], facts["holder"]])
    t = " ".join(w for w in t.split() if not re.search(r"\d", w) and re.sub(r"[^\w/'\-]", "", w).lower() not in NAME_OK)
    d, l = len(DEVA_LETTER.findall(t)), len(LATIN.findall(t))
    return d / (d + l) if d + l else None


def stray_names(text, facts):
    """Capitalised Latin words inside a sentence that are not the given names: invented people, places, brands."""
    allowed = {w.lower() for x in (facts["payee"], facts["company"], facts["holder"]) if x for w in x.split()}
    out = []
    for m in re.finditer(r"(?<![.!?।\n]\s)(?<!^)(?<=\s)([A-Z][a-z][A-Za-z'\-]+)", text):
        w = m.group(1)
        before = text[:m.start()].rstrip()
        if not before or before[-1] in ".!?।:\"'(": continue
        if w.lower() in allowed or w.lower() in NAME_OK or w.lower() in HINGLISH_WORDS: continue
        out.append(w)
    return out


def norm_answer(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\sऀ-ॿ]", " ", s.lower())).strip()


def code_checks(row, world, facts=None):
    """List of failure reasons (empty = pass). Duplicate answers are checked separately (they depend on other rows)."""
    f = facts or e.case_facts(world); bad = []
    op = row.get("opening") or ""; ans = row.get("answers") or {}; lang = row.get("lang"); lab = text_labels(world)
    if not op.strip(): bad.append("empty:opening")
    for k in FIELD_ORDER:
        if not isinstance(ans.get(k), str) or not ans[k].strip(): bad.append(f"empty:{k}")
    if bad: return bad
    if DEVA_DIGIT.search(op + " ".join(ans.values())): bad.append("devanagari_digits")
    if not has_amount(op, f["amount"]): bad.append("amount_missing")
    joined = _join_digits(op)
    if f["account"] not in joined: bad.append("account_missing")
    if f["payee"].lower() not in re.sub(r"\s+", " ", op).lower(): bad.append("payee_missing")
    if f["company"]:
        if f["company"].lower() not in op.lower(): bad.append("company_missing")
    else:
        rest = _strip(op, [f["payee"]])
        if any(c.lower() in rest.lower() for c in ALL_COMPANIES) or COMPANY_WORDS.search(rest): bad.append("company_named_but_not_in_story")
    rest = joined.replace(f["account"], " ")
    if f["phone"]:
        if f["phone"] not in rest: bad.append("phone_missing")
        rest = rest.replace(f["phone"], " ")
    elif re.search(r"\d{10}", rest): bad.append("phone_named_but_not_in_story")
    for form in amount_forms(f["amount"]): rest = re.sub(r"(?<![\d,.])" + re.escape(form) + r"(?!\d|[,.]\d)", " ", rest)
    if re.search(r"\d", rest) and "phone_named_but_not_in_story" not in bad: bad.append("extra_number")
    # reference code: iff a reference is given, and exactly the one code made for this world
    code = ref_code(world["id"]); ref = re.sub(r"\s+", "", ans["reference"]).upper()
    if lab["reference"] == "gave_reference":
        if code.upper() not in ref: bad.append("reference_code_missing")
    elif re.search(r"\d", ans["reference"]): bad.append("reference_given_but_none")
    # nothing beyond the structure
    if lab["opening"] == "bare" and URGENT.search(op): bad.append("bare_has_urgency")
    if lab["opening"] == "benign_reason" and URGENT.search(op): bad.append("benign_has_urgency")
    allowed_story = {"opening": lab["opening"] == "risky_reason", "purpose": lab["purpose"] == "fee_to_get_something" or lab["opening"] == "risky_reason"}
    for part, text in [("opening", op)] + [(k, ans[k]) for k in FIELD_ORDER]:
        if not allowed_story.get(part, False) and STORY.search(text): bad.append(f"story_word:{part}")
        if lang == "en" and stray_names(text, f): bad.append(f"stray_name:{part}")
        if lang == "hi" and part != "reference":
            latin = re.findall(r"[A-Za-z][A-Za-z'\-]+", _strip(text, [f["payee"], f["company"], f["holder"], code]))
            if any(w.lower() not in NAME_OK for w in latin): bad.append(f"stray_latin:{part}")
    # script
    if lang == "hi":
        s = script_share(op, f)
        if s is None or s < .75: bad.append("script:opening_not_devanagari")
        for k in FIELD_ORDER:
            s = script_share(_strip(ans[k], [code]), f)
            if s is not None and s < .6: bad.append(f"script:{k}_not_devanagari")
            if s is None and k != "reference": bad.append(f"script:{k}_no_letters")
    else:
        if DEVA.search(op) or any(DEVA.search(ans[k]) for k in FIELD_ORDER): bad.append("script:devanagari_in_latin_language")
        if lang == "hinglish":
            words = set(re.findall(r"[a-z]+", (op + " " + " ".join(ans.values())).lower()))
            if len(words & HINGLISH_WORDS) < 4: bad.append("script:hinglish_reads_as_english")
    return bad


def dup_limit(norm):
    return SHORT_LIMIT if len(norm.split()) <= SHORT_WORDS else DUP_LIMIT


def dup_check(row, counts):
    """Answers that would pass their limit in this language and split: at most DUP_LIMIT copies of an answer, or
    SHORT_LIMIT for answers of at most SHORT_WORDS words. Copies inside the row itself count too.
    `counts`: Counter of (lang, norm answer) over kept rows."""
    local, bad = Counter(), []
    for k in FIELD_ORDER:
        n = norm_answer(row["answers"][k]); key = (row["lang"], n)
        if counts[key] + local[key] >= dup_limit(n): bad.append(f"duplicate_answer:{k}")   # this copy would pass the limit
        local[key] += 1
    return bad


# ---------------------------------------------------------------- model calls
def _chat(*a, **k):
    import nebius_client
    return nebius_client.chat(*a, **k)


def make_row(world, lang, writer, obj):
    ans = obj.get("answers") if isinstance(obj.get("answers"), dict) else {}
    return {"id": world["id"], "lang": lang, "opening": str(obj.get("opening") or "").strip(),
            "answers": {k: str(ans.get(k) or "").strip() for k in FIELD_ORDER}, "writer": writer,
            "reviewer": writer_reviewer(world["id"])[1], "prompt_version": PROMPT_VERSION, "world_hash": g.params_hash()}


def write_one(world, lang, writer, attempt=0):
    facts = e.case_facts(world)
    msgs = [{"role": "system", "content": WRITER_SYSTEM}, {"role": "user", "content": writer_task(world, facts, lang, attempt)}]
    obj = None
    for max_tokens in (1600, 3200):          # GLM's reasoning counts against max_tokens; retry once with more room
        obj = parse_json(_chat(writer, msgs, max_tokens=max_tokens, temperature=0.9, tag="v4words-write"))
        if isinstance(obj, dict) and "opening" in obj: break
    if not isinstance(obj, dict) or "opening" not in obj: return None, "writer_bad_json"
    return make_row(world, lang, writer, obj) | {"attempt": attempt}, None


def render_item(row):
    return "\n".join([f"Language: {row['lang']}", f"Opening: {row['opening']}"] +
                     [f"{k} (Q: {QUESTIONS[k]}) -> {row['answers'][k]}" for k in FIELD_ORDER])


def _clean_labels(obj):
    if not isinstance(obj, dict): return None
    return {k: str(obj.get(k, "")).strip().lower().replace(" ", "_").replace("-", "_") for k in ["opening"] + FIELD_ORDER}


def review(rows, reviewer, batch=6):
    """Labels read back from the text alone: {id: {opening, field...}} (missing ids could not be parsed)."""
    got = {}

    def run(group, max_tokens):
        user = "\n\n".join(f"### Item {j + 1}\n{render_item(r)}" for j, r in enumerate(group))
        user += f"\n\nClassify each of the {len(group)} items independently. Reply with ONLY the JSON object."
        obj = parse_json(_chat(reviewer, [{"role": "system", "content": REVIEW_SYSTEM}, {"role": "user", "content": user}],
                               max_tokens=max_tokens, temperature=0.0, tag="v4words-review"))
        res = {}
        if isinstance(obj, dict):
            for j, r in enumerate(group):
                lab = _clean_labels(obj.get(str(j + 1)))
                if lab: res[r["id"]] = lab
        return res

    groups = [rows[i:i + batch] for i in range(0, len(rows), batch)]
    if not groups: return got
    got.update(run(groups[0], 400 * len(groups[0]) + 1200))          # warm the cache before going parallel
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(lambda gr: run(gr, 400 * len(gr) + 1200), groups[1:]): got.update(res)
    for r in rows:                                                     # one-by-one retry for anything unparsed
        if r["id"] not in got:
            try: got.update(run([r], 1600))
            except Exception: pass
    return got


def compare(world, labels):
    want = text_labels(world)
    if labels is None: return ["review_unparsed"]
    return [f"review:{k}:{want[k]}->{labels.get(k) or '?'}" for k in want if labels.get(k) != want[k]]


# ---------------------------------------------------------------- the pipeline
def _read(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def paths(name):
    return os.path.join(OUT_DIR, f"words_{name}.jsonl"), os.path.join(OUT_DIR, f"words_{name}.rejected.jsonl")


def run_chunk(worlds, name, threads=6, only=None):
    kept_p, rej_p = paths(name)
    kept_before = _read(kept_p); done = {r["id"] for r in kept_before}
    tries = Counter(r["id"] for r in _read(rej_p))     # attempt number = earlier drops of this world in this split
    todo = [w for w in worlds if w["id"] not in done and (only is None or w["id"] in only)]
    if not todo: return [], [], []
    by_id = {w["id"]: w for w in todo}

    def job(w):
        lang = assign_lang(w["id"]); writer = writer_reviewer(w["id"])[0]
        try: row, err = write_one(w, lang, writer, tries[w["id"]])
        except Exception as ex: row, err = None, f"writer_error:{type(ex).__name__}"
        return w, lang, writer, row, err

    with ThreadPoolExecutor(threads) as ex: written = list(ex.map(job, todo))
    rejected, passed = [], []
    for w, lang, writer, row, err in written:
        bad = [err] if err else code_checks(row, w)
        (rejected.append({"id": w["id"], "lang": lang, "writer": writer, "reasons": bad, "row": row}) if bad else passed.append(row))
    labels = {}
    for reviewer in (GLM, DEEPSEEK):
        rows = [r for r in passed if r["reviewer"] == reviewer]
        if rows:
            try: labels.update(review(rows, reviewer))
            except Exception as ex: print(f"review error {type(ex).__name__}: {ex}", flush=True)
    counts = Counter((r["lang"], norm_answer(a)) for r in kept_before for a in r["answers"].values())
    kept = []
    for r in sorted(passed, key=lambda r: world_index(r["id"])):
        bad = compare(by_id[r["id"]], labels.get(r["id"])) or dup_check(r, counts)
        if bad:
            rejected.append({"id": r["id"], "lang": r["lang"], "writer": r["writer"], "reasons": bad, "row": r, "review": labels.get(r["id"])})
            continue
        kept.append(r); counts.update((r["lang"], norm_answer(a)) for a in r["answers"].values())
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(kept_p, "a") as f:
        for r in kept: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(rej_p, "a") as f:
        for r in sorted(rejected, key=lambda r: world_index(r["id"])):
            f.write(json.dumps(r | {"prompt_version": PROMPT_VERSION, "t": stamp}, ensure_ascii=False) + "\n")
    return written, kept, rejected


def run_pipeline(prefix, n, name, threads=6, start=0, chunk=60, stop_at=None, only=None):
    import nebius_client as nc
    os.makedirs(OUT_DIR, exist_ok=True)
    W, K, R = [], [], []
    for lo in range(start, start + n, chunk):
        if stop_at is not None and nc.spent() >= stop_at:
            print(f"STOP: Nebius ledger ${nc.spent():.3f} >= ${stop_at:.2f}; resume later with the same command", flush=True); break
        worlds = [g.sample_world(f"{prefix}-{i}") for i in range(lo, min(lo + chunk, start + n))]
        try: w, k, r = run_chunk(worlds, name, threads, only)
        except Exception as ex:
            print(f"chunk {lo} failed: {type(ex).__name__}: {ex}; continuing", flush=True); continue
        W += w; K += k; R += r
        print(f"[{name}] {prefix}-{lo}..: wrote {len(w)}, kept {len(k)}; ledger ${nc.spent():.3f}", flush=True)
    summary(W, K, R)
    return K, R


def summary(written, kept, rejected):
    kept_ids = {r["id"] for r in kept}
    for key, label in ((lambda x: x[1], "language"), (lambda x: x[2].split("/")[0], "writer")):
        tot, ok = Counter(), Counter()
        for x in written: tot[key(x)] += 1; ok[key(x)] += x[0]["id"] in kept_ids
        print(f"yield by {label}: " + ", ".join(f"{k} {ok[k]}/{tot[k]} ({100 * ok[k] / tot[k]:.0f}%)" for k in sorted(tot)))
    reasons = Counter(re.sub(r"->.*", "", s) for r in rejected for s in set(r["reasons"]))
    print("rejection reasons (rows):", ", ".join(f"{k} {v}" for k, v in reasons.most_common(15)))


# ---------------------------------------------------------------- diversity report
def masked_opening(row):
    f = e.case_facts(g.sample_world(row["id"])); t = row["opening"]
    for x in (f["payee"], f["company"], f["holder"]):
        if x: t = re.sub(re.escape(x), "N", t, flags=re.I)
    return re.sub(r"[\d,]+", "D", t)


def diversity(rows, threshold=.75):
    """Shared frames: pairs of same-language openings whose masked text is more than `threshold` similar. Duplicate
    sentences: answers (normalised) that occur more often than their limit in one language."""
    import difflib
    by = {}
    for r in rows: by.setdefault(r["lang"], []).append(masked_opening(r))
    pairs = 0; rows_in_pair = 0
    for lang, ops in by.items():
        hit = set()
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                sm = difflib.SequenceMatcher(None, ops[i], ops[j])
                if sm.real_quick_ratio() > threshold and sm.quick_ratio() > threshold and sm.ratio() > threshold:
                    pairs += 1; hit |= {i, j}
        rows_in_pair += len(hit)
    c = Counter((r["lang"], norm_answer(a)) for r in rows for a in r["answers"].values())
    over = {k: v for k, v in c.items() if v > dup_limit(k[1])}
    return {"frame_pairs": pairs, "rows_sharing_a_frame": rows_in_pair, "answers_over_limit": len(over),
            "max_answer_repeat": max(c.values()) if c else 0, "top_repeats": sorted(over.items(), key=lambda x: -x[1])[:5]}


# ---------------------------------------------------------------- RULE V4-4: the leak audit
def structure_logit(world, payee_type=True):
    """Logit of P(scam | the three cues and the eight answers the text carries), exact: the prior times the cue and
    field likelihood columns, skipping the RECORDS and LOOKUPS tables. The likelihood tables are read with the full
    context because some depend on records (whether a call is live, whether credits came). Text-level categories:
    a given reference (verified or failed, which the text cannot show) is the sum of the two columns.
    payee_type=True also multiplies the payee_type record's likelihood: the payee's name form (a person's name, or a
    name ending in "Traders") follows that record, which the agent sees, so it counts as structure, not as a leak."""
    ctx = g.context(world); w = g.prior(0.5).copy()
    if payee_type: w = w * g.lik(g.RECORDS, "payee_type", ctx)[:, g.RECORDS["payee_type"][0].index(world["records"]["payee_type"])]
    for name in g.CUES: w = w * g.lik(g.CUES, name, ctx)[:, g.CUES[name][0].index(world["cues"][name])]
    for f in g.FIELDS:
        vals, L, a = g.FIELDS[f][0], g.lik(g.FIELDS, f, ctx), world["answers"][f]
        col = L[:, vals.index("verified")] + L[:, vals.index("failed")] if f == "reference" and a != "none" else L[:, vals.index(a)]
        w = w * col
    p = min(max(g.p_scam_given(w), 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


TOKEN = re.compile(r"[a-z]+|[ऀ-ॣॱ-ॿ]+")


def row_text(row, mask=False):
    t = row["opening"] + " " + " ".join(row["answers"][k] for k in FIELD_ORDER)
    if mask:
        f = e.case_facts(g.sample_world(row["id"]))
        t = _strip(t, [f["payee"], f["company"], f["holder"], ref_code(row["id"])])
        for c in ALL_COMPANIES: t = _strip(t, [c])
        t = re.sub(r"\btraders\b", " ", t, flags=re.I)
    return t


CS = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0)


def audit(rows, mask=False, folds=5, seed=0, payee_type=True):
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
    from sklearn.metrics import log_loss
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from scipy.sparse import csr_matrix, hstack
    worlds = [g.sample_world(r["id"]) for r in rows]
    y = np.array([w["story"]["truth"] == "scam" for w in worlds], dtype=int)
    z = np.array([[structure_logit(w, payee_type)] for w in worlds])
    vec = CountVectorizer(binary=True, min_df=3, tokenizer=lambda s: TOKEN.findall(s.lower()), token_pattern=None, lowercase=False)
    X = vec.fit_transform([row_text(r, mask) for r in rows])
    Xb = hstack([csr_matrix(z), X]).tocsr()
    cv = StratifiedKFold(folds, shuffle=True, random_state=seed)
    # (a) one feature, effectively unpenalised. (b) the L2 strength is picked inside each training fold by an inner
    # 5-fold search on log-loss, so an over-fitted bag of words cannot hide a real leak behind added noise.
    la_m = lambda: LogisticRegression(C=1e4, max_iter=5000)
    lb_m = lambda: LogisticRegressionCV(Cs=list(CS), cv=5, scoring="neg_log_loss", max_iter=5000)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        pa = cross_val_predict(la_m(), z, y, cv=cv, method="predict_proba")[:, 1]
        pb = cross_val_predict(lb_m(), Xb, y, cv=cv, method="predict_proba")[:, 1]
        full = lb_m().fit(Xb, y)
    la, lb = log_loss(y, pa), log_loss(y, pb)
    coef = full.coef_[0][1:]; vocab = np.array(vec.get_feature_names_out())
    df = np.asarray(X.sum(axis=0)).ravel()
    top = [(vocab[i], round(float(coef[i]), 3), int(df[i])) for i in np.argsort(-np.abs(coef))[:20]]
    gain = la - lb
    return {"n": len(rows), "scam_share": float(y.mean()), "mask_fixed_names": mask, "payee_type_in_structure": payee_type, "logloss_structure": la,
            "logloss_structure_plus_words": lb, "gain": gain, "pass": gain <= 0.02, "top_tokens": top,
            "structure_coef": float(full.coef_[0][0]), "vocab": len(vocab), "C_full": float(full.C_[0])}


def leak_rows(rows, tokens):
    """Ids of rows whose text contains any of the given leak tokens."""
    tok = set(tokens)
    return [r["id"] for r in rows if tok & set(TOKEN.findall(row_text(r).lower()))]


def audit_markdown(name, runs):
    """runs: list of (label, result). The first is the rule's number."""
    first = runs[0][1]
    L = [f"# RULE V4-4 leak audit: words_{name}\n",
         f"{first['n']} kept rows, scam share {first['scam_share']:.2f}. 5-fold logistic regression, held-out log-loss (nats). "
         f"Words model: L2 strength chosen by inner 5-fold CV from {list(CS)}. Structure = exact posterior given the three cues "
         f"and the eight answers the text carries, with or without the payee_type record (it sets the payee's name form).\n",
         "| variant | structure only | structure + words | gain | rule (gain <= 0.02) | C chosen on all rows |", "|---|---|---|---|---|---|"]
    for lab, r in runs:
        L.append(f"| {lab} | {r['logloss_structure']:.4f} | {r['logloss_structure_plus_words']:.4f} | {r['gain']:+.4f} | "
                 f"{'PASS' if r['pass'] else 'FAIL'} | {r['C_full']} |")
    for lab, r in runs:
        L += ["", f"Top 20 leak-weighted tokens, {lab} (positive = toward scam; coef, rows containing it):", ""]
        L.append(", ".join(f"`{t}` {c:+.2f} ({d})" for t, c, d in r["top_tokens"]))
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- CLI
def main(argv):
    if argv and argv[0] == "audit":
        ap = argparse.ArgumentParser(prog="bankdesk_v4_words.py audit")
        ap.add_argument("--name", default="train"); ap.add_argument("--out"); ap.add_argument("--emit-ids")
        ap.add_argument("--regime", default="base", choices=list(g.REGIMES),
                        help="regime the rows' worlds were sampled under; the structure posterior uses the same regime")
        a = ap.parse_args(argv[1:])
        g.set_regime(a.regime)
        rows = _read(paths(a.name)[0])
        wrong = [r["id"] for r in rows if r.get("world_hash", g.params_hash()) != g.params_hash()]
        if wrong: raise SystemExit(f"{len(wrong)} rows (e.g. {wrong[0]}) were written under another world_hash than regime "
                                   f"{a.regime} ({g.params_hash()}); pass the matching --regime")
        raw = audit(rows); raw_nopt = audit(rows, payee_type=False); masked = audit(rows, mask=True)
        md = audit_markdown(a.name, [("raw text, structure with payee_type (the rule)", raw),
                                     ("raw text, structure without payee_type", raw_nopt),
                                     ("fixed names masked, with payee_type (secondary)", masked)])
        if a.regime != "base":
            md = md.replace("\n\n", f"\n\nRegime: {a.regime} (params hash {g.params_hash()}); worlds and the structure posterior "
                                    f"are both computed under it.\n\n", 1)
        print(md)
        out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "bankdesk_v4", f"AUDIT_{a.name}.md")
        os.makedirs(os.path.dirname(out), exist_ok=True); open(out, "w").write(md)
        json.dump({"regime": a.regime, "params_hash": g.params_hash(), "raw": raw, "raw_without_payee_type": raw_nopt, "masked": masked},
                  open(out.replace(".md", ".json"), "w"), indent=1, ensure_ascii=False)
        if a.emit_ids:
            ids = leak_rows(rows, [t for t, _, _ in raw["top_tokens"]])
            open(a.emit_ids, "w").write("\n".join(ids) + "\n"); print(f"{len(ids)} rows contain a top leak token -> {a.emit_ids}")
        return 0 if raw["pass"] else 1
    if argv and argv[0] in ("write", "diversity"):
        cmd, argv = argv[0], argv[1:]
    else: cmd = "write"
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="pilot"); ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--start", type=int, default=0); ap.add_argument("--name", default="pilot")
    ap.add_argument("--threads", type=int, default=6); ap.add_argument("--chunk", type=int, default=60)
    ap.add_argument("--stop-at", type=float, help="stop before a chunk once the Nebius ledger reaches this total ($)")
    ap.add_argument("--only", help="file of world ids: (re)write only these, after removing them from the kept file")
    ap.add_argument("--regime", default="base", choices=list(g.REGIMES), help="regime the worlds are sampled under")
    a = ap.parse_args(argv)
    g.set_regime(a.regime)
    if cmd == "diversity":
        print(json.dumps(diversity(_read(paths(a.name)[0])), ensure_ascii=False, indent=1)); return 0
    only = None
    if a.only:
        only = {l.strip() for l in open(a.only) if l.strip()}
        kept_p = paths(a.name)[0]; rows = _read(kept_p)
        drop = [r for r in rows if r["id"] in only]
        with open(paths(a.name)[1], "a") as f:      # the replaced rows are logged, not lost
            for r in drop: f.write(json.dumps({"id": r["id"], "lang": r["lang"], "writer": r["writer"], "reasons": ["replaced_after_audit"],
                                               "row": r, "prompt_version": r.get("prompt_version"), "t": time.strftime("%Y-%m-%dT%H:%M:%S")},
                                              ensure_ascii=False) + "\n")
        with open(kept_p, "w") as f:
            for r in rows:
                if r["id"] not in only: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    run_pipeline(a.prefix, a.n, a.name, a.threads, a.start, a.chunk, a.stop_at, only)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
