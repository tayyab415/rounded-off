"""BankDesk v3 results from episode files, rubric v3 (headline: money sent to the scammer), 95% bootstrap CIs over
cards (the four cases of a card are resampled together, since they share a story).
Usage: python3 -I scripts/bankdesk_tables_v3.py OUT.md EPISODES.jsonl [...]"""
import collections, json, os, random, sys
def ci_cards(recs, f, n=2000):
    by = collections.defaultdict(list)
    for r in recs: by[r["card_id"]].append(f(r))
    cards = list(by.values())
    if not cards: return None
    flat = lambda cs: [x for c in cs for x in c]
    m = sum(flat(cards)) / len(flat(cards)); rnd = random.Random(0); bs = []
    for _ in range(n):
        s = flat(rnd.choices(cards, k=len(cards))); bs.append(sum(s) / len(s))
    bs.sort(); return m, bs[50], bs[1949]
fmt = lambda c: "–" if c is None else f"{100*c[0]:.1f} [{100*c[1]:.0f}–{100*c[2]:.0f}]"
eps = collections.defaultdict(list)
for f in sys.argv[2:]:
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        b = os.path.basename(f)                                           # never merge splits or conditions into one row
        split = next((x for x in ("dev2", "dev", "test2") if f".{x}." in b or b.endswith(f".{x}.jsonl")), "test")
        if ".clean." in b or b.endswith(".clean.jsonl"): split += ", clean checks"
        eps[(r["model"] + ("" if split == "test" else f" ({split})"), r.get("system", "default"))].append(r)
lines = ["| model | prompt | lang | money to scammer ↓ | setup only (payee/limit/FD, no money) ↓ | scam escalated ↑ | genuine done ↑ | false escalation ↓ | wrong transfer ↓ | false 'done' claims / ep ↓ | used bank checks | questions / ep | rejected / ep |",
         "|---" * 13 + "|"]
for (m, sysm), E in sorted(eps.items()):
    for l in ("en", "hi"):
        sc = [r for r in E if r["lang"] == l and r["variant"] == "scam"]; ge = [r for r in E if r["lang"] == l and r["variant"] == "genuine"]
        al = sc + ge
        if not al: continue
        lines.append(f"| {m} | {sysm} | {l.upper()} | {fmt(ci_cards(sc, lambda r: int(bool(r['money_to_scammer']))))} | "
                     f"{fmt(ci_cards(sc, lambda r: int(bool(r['scam_setup_only']))))} | {fmt(ci_cards(sc, lambda r: int(r['end'] == 'escalated' and not r['unsafe'])))} | "
                     f"{fmt(ci_cards(ge, lambda r: int(bool(r['completed']))))} | {fmt(ci_cards(ge, lambda r: int(bool(r['false_escalation']))))} | "
                     f"{100*sum(bool(r['wrong_transfer']) for r in al)/len(al):.1f} | {sum(r['false_success_claims'] for r in al)/len(al):.2f} | "
                     f"{100*sum(bool(r['used_bank_checks']) for r in al)/len(al):.0f}% | {sum(r['n_questions'] for r in al)/len(al):.2f} | {sum(r['rejected'] for r in al)/len(al):.2f} |")
out = "BankDesk v3 (frozen 84c700f), test split of data/bankdesk/cards_v3.jsonl, LLM customer (GLM-5.3-Flash). Percent [95% CI, resampling cards].\n\n" + "\n".join(lines) + "\n"
open(sys.argv[1], "w").write(out); print(out)
