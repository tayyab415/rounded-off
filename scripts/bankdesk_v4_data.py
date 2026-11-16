"""BankDesk v4: build training rows from the generator's exact action values. Design: notes/BANKDESK_V4_DESIGN.md s.15.

Two sources of states, one labeller:
  expert   play each world K times, sampling every action from soft_targets (softmax of exact value / tau). These are
           the round-0 rows: near-best actions in proportion to how close they are, so the policy is not peaked.
  dagger   take episodes a student model played (a runs .jsonl from bankdesk_v4_run.py), revisit every state the
           student reached, and label it the same way. The student's own mistakes get covered.
Each row is one decision: the chat so far and one target action. No language model is called here. The wording of
form fields and of the final message comes from templates in the customer's language, with the message naming the
facts that moved the risk most (computed from the generator).

  python3 scripts/bankdesk_v4_data.py expert --prefix train --n 600 --k 3 --out data/bankdesk_v4/sft_r0.jsonl
  python3 scripts/bankdesk_v4_data.py dagger --runs runs/bankdesk_v4/r0/dev.jsonl --out data/bankdesk_v4/dagger_r1.jsonl
"""
import argparse, json, os, random, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bankdesk_v4 as g
import bankdesk_v4_env as e

# ---------------------------------------------------------------- wording templates (English, Hindi, Hinglish)
LABELS = {
    "hi": {"purpose": "यह भुगतान किस लिए है?", "met_payee": "क्या आप इस व्यक्ति से मिले हैं या इस दुकान पर गए हैं?",
           "reference": "इनवॉइस या बिल नंबर, और व्यवसाय हो तो GSTIN", "on_call_now": "क्या अभी कोई आपसे फ़ोन पर बात करते हुए यह भुगतान करवा रहा है?",
           "told_secret": "क्या किसी ने आपसे यह भुगतान गुप्त रखने को कहा है?",
           "bait_explain": "इस हफ़्ते आपको नए लोगों से छोटी रकम मिली है। क्या उनका इस भुगतान से संबंध है?",
           "how_got_details": "आपको यह खाता नंबर कैसे मिला?", "who_started": "यह भुगतान करने का फ़ैसला आपका अपना है, या किसी ने कहा?"},
    "hinglish": {"purpose": "Yeh payment kis liye hai?", "met_payee": "Kya aap is vyakti se mile hain ya is dukaan par gaye hain?",
                 "reference": "Invoice ya bill number, aur business ho to GSTIN", "on_call_now": "Kya abhi koi aapse phone par baat karte hue yeh payment karwa raha hai?",
                 "told_secret": "Kya kisi ne aapse yeh payment secret rakhne ko kaha hai?",
                 "bait_explain": "Is hafte aapko naye logon se chhoti rakam mili hai. Kya unka is payment se sambandh hai?",
                 "how_got_details": "Aapko yeh account number kaise mila?", "who_started": "Yeh payment karne ka faisla aapka apna hai, ya kisi ne kaha?"},
}
REASONS = {   # (variable, value) -> the fact as the bank would say it to the customer
    ("payee_age", "new"): ("this account was opened very recently", "यह खाता हाल ही में खुला है", "yeh account abhi haal hi mein khula hai"),
    ("senders_today", "many"): ("many different people have paid into it today", "आज इसमें कई अलग-अलग लोगों ने पैसे डाले हैं", "aaj isme kai alag logon ne paise daale hain"),
    ("fast_withdrawal", "yes"): ("money leaves this account within minutes of arriving", "इस खाते से पैसा आते ही निकल जाता है", "is account se paisa aate hi nikal jaata hai"),
    ("reports", "yes"): ("other customers have reported this account", "दूसरे ग्राहकों ने इस खाते की शिकायत की है", "doosre customers ne is account ki shikayat ki hai"),
    ("bait_credits", "yes"): ("you received small credits from strangers this week", "इस हफ़्ते आपको अनजान लोगों से छोटी रकम मिली है", "is hafte aapko anjaan logon se chhoti rakam mili hai"),
    ("call", "unsaved_long"): ("you are on a long call with a number that is not in your contacts", "आप एक अनजान नंबर से लंबी कॉल पर हैं", "aap ek anjaan number se lambi call par hain"),
    ("screen_share", "yes"): ("a screen-sharing app is running on your phone", "आपके फ़ोन पर स्क्रीन शेयरिंग चल रही है", "aapke phone par screen sharing chal rahi hai"),
    ("recent_change", "yes"): ("your limit was raised or a deposit was broken in the last two days", "पिछले दो दिन में आपकी लिमिट बढ़ी या एफ़डी तोड़ी गई है", "pichhle do din mein aapki limit badhi ya FD todi gayi hai"),
    ("past_hold", "yes"): ("we held a payment of yours this week", "इस हफ़्ते हमने आपका एक भुगतान रोका था", "is hafte humne aapka ek payment roka tha"),
    ("registry", "not_found"): ("the company you named is not in the company register", "आपने जो कंपनी बताई वह कंपनी रजिस्टर में नहीं है", "aapne jo company batayi woh company register mein nahi hai"),
    ("number", "some"): ("the phone number you were contacted from has been reported", "जिस नंबर से आपसे संपर्क हुआ उसकी शिकायतें हैं", "jis number se aapse contact hua uski shikayatein hain"),
    ("domain", "new"): ("the company's website was created only days ago", "कंपनी की वेबसाइट कुछ ही दिन पहले बनी है", "company ki website kuch hi din pehle bani hai"),
    ("reference", "failed"): ("the reference you gave does not match any record", "आपने जो रेफ़रेंस दिया वह किसी रिकॉर्ड से नहीं मिलता", "aapne jo reference diya woh kisi record se match nahi karta"),
    ("purpose", "fee_to_get_something"): ("you are paying a fee to receive a job, a loan, a prize or a refund", "आप नौकरी, लोन, इनाम या रिफ़ंड पाने के लिए फ़ीस दे रहे हैं", "aap naukri, loan, inaam ya refund paane ke liye fees de rahe hain"),
    ("met_payee", "no"): ("you have never met the person you are paying", "आप जिसे पैसे भेज रहे हैं उससे कभी मिले नहीं हैं", "aap jise paise bhej rahe hain usse kabhi mile nahi hain"),
    ("told_secret", "yes"): ("someone asked you to keep this payment secret", "किसी ने आपसे यह भुगतान गुप्त रखने को कहा है", "kisi ne aapse yeh payment secret rakhne ko kaha hai"),
    ("on_call_now", "yes"): ("someone is guiding you through this payment on a call", "कोई फ़ोन पर आपसे यह भुगतान करवा रहा है", "koi phone par aapse yeh payment karwa raha hai"),
    ("bait_explain", "from_this_work", ): ("the small credits you received are tied to this payment", "आपको मिली छोटी रकम इसी भुगतान से जुड़ी है", "aapko mili chhoti rakam isi payment se judi hai"),
    ("who_started", "someone_asked"): ("someone else asked you to make this payment", "किसी और ने आपसे यह भुगतान करने को कहा है", "kisi aur ne aapse yeh payment karne ko kaha hai"),
    ("how_got_details", "phone_call"): ("you were given this account number over a phone call", "यह खाता नंबर आपको फ़ोन कॉल पर दिया गया", "yeh account number aapko phone call par diya gaya"),
}
LANG_IX = {"en": 0, "hi": 1, "hinglish": 2}
MESSAGES = {
    "pay": ("Your payment of Rs {amount} to {payee} is ready. Please approve it in your app.",
            "{payee} को Rs {amount} का भुगतान तैयार है। कृपया अपने ऐप में इसे मंज़ूर करें।",
            "{payee} ko Rs {amount} ka payment taiyaar hai. Kripya apne app mein approve karein."),
    "delay": ("We are holding this payment of Rs {amount} for one hour because {why}. You can cancel it in that time. If anyone is pressing you to pay, call 1930.",
              "हम Rs {amount} का यह भुगतान एक घंटे के लिए रोक रहे हैं क्योंकि {why}। इस बीच आप इसे रद्द कर सकते हैं। अगर कोई आप पर भुगतान का दबाव डाल रहा है तो 1930 पर कॉल करें।",
              "Hum Rs {amount} ka yeh payment ek ghante ke liye rok rahe hain kyunki {why}. Is beech aap ise cancel kar sakte hain. Agar koi aap par payment ka dabaav daal raha hai to 1930 par call karein."),
    "hold": ("We have stopped this payment of Rs {amount} because {why}. Please do not send money or share any OTP. Our fraud team will call you on your registered number. You can also call 1930 or report at cybercrime.gov.in.",
             "हमने Rs {amount} का यह भुगतान रोक दिया है क्योंकि {why}। कृपया पैसे न भेजें और कोई ओटीपी साझा न करें। हमारी टीम आपके रजिस्टर्ड नंबर पर कॉल करेगी। आप 1930 पर कॉल या cybercrime.gov.in पर शिकायत भी कर सकते हैं।",
             "Humne Rs {amount} ka yeh payment rok diya hai kyunki {why}. Kripya paise na bhejein aur koi OTP share na karein. Hamari team aapke registered number par call karegi. Aap 1930 par call ya cybercrime.gov.in par report bhi kar sakte hain."),
}
NO_REASON = ("some details of this payment do not match what we expect", "इस भुगतान की कुछ बातें मेल नहीं खातीं", "is payment ki kuch baatein match nahi kartin")
JOIN = (" and ", " और ", " aur ")
WORDED = False      # phase one: forms list bare fact names and the bank words the questions. Phase two turns this on.


def top_reasons(ep, k=2):
    """The observed facts that push hardest toward a scam: log of P(fact | scam) / P(fact | genuine), largest first."""
    pr = g.prior(ep.p_scam); out = []
    for table, obs in ((g.RECORDS, ep.world["records"]), (g.CUES, ep.world["cues"]), (g.LOOKUPS, ep.lookups), (g.FIELDS, ep.answers)):
        for name, val in obs.items():
            if (name, val) not in REASONS: continue
            col = g.lik(table, name, ep.ctx)[:, table[name][0].index(val)]
            ps = (pr * col)[g.IS_SCAM].sum() / pr[g.IS_SCAM].sum(); pg = (pr * col)[~g.IS_SCAM].sum() / pr[~g.IS_SCAM].sum()
            if ps > pg: out.append((float(np.log(ps / max(pg, 1e-9))), name, val))
    return [(n, v) for _, n, v in sorted(out, reverse=True)[:k]]


def message_for(ep, action):
    ix = LANG_IX.get(ep.case["lang"], 0)
    why = JOIN[ix].join(REASONS[r][ix] for r in top_reasons(ep)) or NO_REASON[ix]
    return MESSAGES[action][ix].format(amount=f"{ep.case['amount']:,}", payee=ep.case["payee"], why=why)


def action_text(ep, cand):
    """The target line for a candidate action, worded in the customer's language."""
    _, kind, detail, _ = cand
    if kind == "lookup": return f"ACTION: lookup({detail})"
    if kind == "form": return e.render_form(detail, LABELS.get(ep.case["lang"]) if WORDED else None)
    risk, action = detail
    return f'ACTION: decide(risk={risk}, action={action}, message="{message_for(ep, action)}")'


# ---------------------------------------------------------------- rows
def _row(ep, cand, prob, source, world_id):
    return {"id": world_id, "lang": ep.case["lang"], "step": len(ep.log), "source": source, "kind": cand[1], "value": float(cand[0]),
            "best_value": float(e.candidates(ep)[0][0]), "prob": prob,
            "messages": e.messages(ep) + [{"role": "assistant", "content": action_text(ep, cand)}]}


def expert_rows(job):
    world_id, k, tau, seed, words = job
    world = g.sample_world(world_id); rows = []
    for j in range(k):
        rnd = random.Random(f"{seed}-{world_id}-{j}"); ep = e.Episode(world, words=words)
        while not ep.done:
            st = e.soft_targets(ep, tau); prob, cand = rnd.choices(st, weights=[p for p, _ in st])[0]
            rows.append(_row(ep, cand, prob, "expert", world_id)); ep.step(rows[-1]["messages"][-1]["content"])
    seen, out = set(), []
    for r in rows:      # the same state with the same target once only
        key = json.dumps(r["messages"], ensure_ascii=False, sort_keys=True)
        if key not in seen: seen.add(key); out.append(r)
    return out


def dagger_rows(job):
    rec, tau, seed, words = job
    world = g.sample_world(rec["id"]); ep = e.Episode(world, words=words); rows = []
    rnd = random.Random(f"{seed}-{rec['id']}")
    for turn in rec["turns"]:
        if ep.done: break
        st = e.soft_targets(ep, tau); prob, cand = rnd.choices(st, weights=[p for p, _ in st])[0]
        rows.append(_row(ep, cand, prob, "dagger", rec["id"])); ep.step(turn["raw"])      # label the state, then follow the student
    return rows


def load_words(path):
    return {json.loads(l)["id"]: json.loads(l) for l in open(path, encoding="utf-8")} if path else {}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("expert"); a1.add_argument("--prefix", required=True); a1.add_argument("--n", type=int, required=True)
    a1.add_argument("--k", type=int, default=3); a1.add_argument("--start", type=int, default=0)
    a2 = sub.add_parser("dagger"); a2.add_argument("--runs", required=True)
    for a in (a1, a2):
        a.add_argument("--out", required=True); a.add_argument("--tau", type=float, default=0.02); a.add_argument("--seed", default="v4")
        a.add_argument("--words"); a.add_argument("--procs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
        a.add_argument("--only-with-words", action="store_true")
    a = ap.parse_args(); words = load_words(a.words)
    if a.cmd == "expert":
        ids = [f"{a.prefix}-{i}" for i in range(a.start, a.start + a.n)]
        if a.only_with_words: ids = [i for i in ids if i in words]
        jobs = [(i, a.k, a.tau, a.seed, words.get(i)) for i in ids]; fn = expert_rows
    else:
        recs = [json.loads(l) for l in open(a.runs, encoding="utf-8")]
        jobs = [(r, a.tau, a.seed, words.get(r["id"])) for r in recs]; fn = dagger_rows
    with ProcessPoolExecutor(a.procs) as ex: chunks = list(ex.map(fn, jobs, chunksize=4))
    rows = [r for c in chunks for r in c]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = {k: sum(r["kind"] == k for r in rows) for k in ("lookup", "form", "decide")}
    regret = float(np.mean([r["best_value"] - r["value"] for r in rows])) if rows else 0.0
    print(json.dumps({"rows": len(rows), "worlds": len(jobs), "kinds": kinds, "mean_value_given_up_by_soft_targets": round(regret, 4),
                      "langs": {l: sum(r["lang"] == l for r in rows) for l in ("en", "hi", "hinglish")}, "generator": g.params_hash()}))
