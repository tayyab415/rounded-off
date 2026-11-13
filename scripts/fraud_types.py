"""Bank red-team harmful-answer rate by fraud type (English), from judged files.

Fraud type comes from keyword rules on the prompt, first match wins; rough, and shown as such in the article.
Usage: python3 -I scripts/fraud_types.py JUDGED_DIR MODEL_TAG [MODEL_TAG ...]
"""
import collections, glob, json, os, re, sys
CATS = [("OTP / phishing / vishing", r"\botp\b|phish|vish|sms|caller|impersonat|fake (call|message|website|link)"),
        ("stolen cards / card testing", r"cvv|card numbers|stolen card|data breach|card testing|carding|skimm"),
        ("forged KYC / identity", r"aadhaar|\bpan\b|kyc|forg|fake (id|document|salary|payslip)|identity"),
        ("false dispute / chargeback", r"chargeback|dispute|false claim|claim .* (stolen|unauthori)|refund"),
        ("mule accounts / laundering", r"mule|launder|structur|threshold|cash deposit|hawala|in (their|his|her) names?|move money"),
        ("insider / data theft", r"employee|insider|database|work (at|in) .*bank|customer (list|data)")]
def cat(p):
    p = p.lower()
    for name, rx in CATS:
        if re.search(rx, p): return name
    return "other"
prompts = [json.loads(l) for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "eval", "bank_redteam_en.jsonl"))]
n = collections.Counter(cat(r["prompt"]) for r in prompts)
src, models = sys.argv[1], sys.argv[2:]
H = {}
for m in models:
    for l in (l for f in glob.glob(f"{src}/{m}.en*.jsonl") for l in open(f)):
        r = json.loads(l)
        if r["set"] != "bank_redteam": continue
        H.setdefault(m, collections.Counter())[cat(r["prompt"])] += int(r.get("guard_safety") == "Unsafe" and r.get("behavior") == "answered")
print("| fraud type | n | " + " | ".join(models) + " |"); print("|---" * (len(models) + 2) + "|")
for c, _ in CATS + [("other", "")]:
    print(f"| {c} | {n[c]} | " + " | ".join(f"{100*H[m][c]/n[c]:.0f}" if n[c] else "-" for m in models) + " |")
