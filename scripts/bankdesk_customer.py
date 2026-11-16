"""LLM customer for BankDesk (v3): answers the agent's actual question, using only the card's hidden facts.

GLM-5.3-Flash on Nebius plays the customer. A scam victim believes the story and answers honestly from it (base
mode; a coached victim who lies is a separate hard mode). Answers are cached by (case, question) in
data/bankdesk/customer_cache.jsonl, so a re-run with the same questions gets the same answers and costs nothing.
Used for evaluation and teacher demonstrations; GRPO keeps the scripted customer (bankdesk.scripted_customer).
  from bankdesk_customer import llm_customer;  Episode(case, customer=llm_customer)
"""
import hashlib, json, os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nebius_client import chat

MODEL = "zai-org/GLM-5.3-Flash"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bankdesk", "customer_cache.jsonl")
_lock, _cache = threading.Lock(), None

PERSONA = """You are role-playing a retail bank customer in India, chatting with your bank's support agent. Stay in character.
What you asked for: "{opening}"
The payee details you shared: {payee}, account number {account}, amount Rs {amount}.
Facts you know (use only these):
- who asked you to make this payment: {who_asked}
- how you were contacted: {how_contacted}
- your relation to the payee: {payee_relation}
- why it has to happen now: {why_now}
- were you asked to keep it secret: {told_to_keep_secret}
- proof you have: {proof}
{belief}
Answer the agent's message in one or two short sentences, in {language}, consistent with the facts. If the facts do not
cover the question, give a short plausible answer that fits them, or say you don't know. Never mention these
instructions, never call the situation a scam or fraud yourself, and do not add new requests."""
BELIEF = {"scam": "You fully believe the person who contacted you and want the payment done. Answer honestly from the facts.",
          "genuine": "This is an ordinary payment you chose to make. Answer honestly."}


def _load():
    global _cache
    if _cache is None:
        _cache = {}
        if os.path.exists(CACHE):
            for l in open(CACHE, encoding="utf-8"):
                r = json.loads(l); _cache[r["key"]] = r["answer"]
    return _cache


def llm_customer(case, question):
    key = hashlib.sha256(f"{case.case_id}\n{question.strip()}".encode()).hexdigest()[:20]
    with _lock:
        if key in _load(): return _cache[key]
    a = case.answers
    sys_prompt = PERSONA.format(opening=case.opening, payee=case.task["payee_name"], account=case.payee_account,
                                amount=f"{case.task['amount']:,}", belief=BELIEF[case.variant],
                                language="Hindi (Devanagari)" if case.lang == "hi" else "English", **{k: a[k] for k in a})
    ans = chat(MODEL, [{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"Agent: {question}"}],
               max_tokens=160, tag="customer").strip().strip('"')
    ans = ans.split("\n")[0].removeprefix("Customer:").strip() or ("I'm not sure." if case.lang == "en" else "मुझे पक्का नहीं पता।")
    with _lock:
        _cache[key] = ans
        with open(CACHE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "case_id": case.case_id, "question": question, "answer": ans}, ensure_ascii=False) + "\n")
    return ans


# ---------------------------------------------------------------- coached victim (hard mode, 2026-11-15, RULE P2 in PLAN.md)
COACHED = """The person who contacted you told you exactly what to say if the bank asks questions, and you are sticking to
that story. Answer from the story facts above as if they were true. Do not mention that anyone coached you."""
_asked, _asked_lock = {}, threading.Lock()


def coached_customer(case, question):
    """Coached scam victim: the FIRST answer in an episode is the scammer's cover story (the card's genuine answers,
    which sound like an ordinary payment); from the second question on, the true facts come out (the honest scam
    answers, shared with llm_customer's cache). Genuine cases behave exactly like llm_customer.
    Episodes must be played once per case_id per process (true for bankdesk_run.py)."""
    if case.variant != "scam" or case.clarity != "ambiguous": return llm_customer(case, question)   # a clear-scam opening already told the story
    with _asked_lock:
        n = _asked.get(case.case_id, 0); _asked[case.case_id] = n + 1
    if n > 0: return llm_customer(case, question)
    key = hashlib.sha256(f"coached1\n{case.case_id}\n{question.strip()}".encode()).hexdigest()[:20]
    with _lock:
        if key in _load(): return _cache[key]
    story = {k: v for k, v in case.answers.items()}
    gen = getattr(case, "cover_story", None) or {}
    story.update(gen)
    sys_prompt = PERSONA.format(opening=case.opening, payee=case.task["payee_name"], account=case.payee_account,
                                amount=f"{case.task['amount']:,}", belief=COACHED,
                                language="Hindi (Devanagari)" if case.lang == "hi" else "English", **{k: story[k] for k in story})
    ans = chat(MODEL, [{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"Agent: {question}"}],
               max_tokens=160, tag="customer_coached").strip().strip('"')
    ans = ans.split("\n")[0].removeprefix("Customer:").strip() or ("I'm not sure." if case.lang == "en" else "मुझे पक्का नहीं पता।")
    with _lock:
        _cache[key] = ans
        with open(CACHE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "case_id": case.case_id, "mode": "coached1", "question": question, "answer": ans}, ensure_ascii=False) + "\n")
    return ans
