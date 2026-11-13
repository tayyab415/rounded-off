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
