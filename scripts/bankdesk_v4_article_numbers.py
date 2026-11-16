"""Numbers for the article's BankDesk v4 section (7.10): how the trained v3 agent decides, and what the v4 simulator shows.

Reads saved files only; runs no model. Writes results/bankdesk_v4/ARTICLE_NUMBERS.{json,md}.
  python3 -I scripts/bankdesk_v4_article_numbers.py
Sources:
  results/raw/hf_runs/bankdesk/e374042/GRPO3.default.jsonl   GRPO3 on the 111 test cards (the run behind 7.8's headline)
  data/bankdesk/cards_v3.jsonl                               the v3 scenario cards
  results/bankdesk_v4/RULE1.json                             the v4 generator check (scripts/bankdesk_v4.py rule1)
"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bankdesk as bd
from bankdesk_run import load_cases
from bankdesk_rules_baseline import flags_from_signals

EPISODES = os.path.join(ROOT, "results/raw/hf_runs/bankdesk/e374042/GRPO3.default.jsonl")
CARDS = os.path.join(ROOT, "data/bankdesk/cards_v3.jsonl")
RULE1 = os.path.join(ROOT, "results/bankdesk_v4/RULE1.json")
# Written once, before looking at how it scores, from the words scam victims use about who contacted them.
KEYWORDS = r"whatsapp|telegram|sms|unsolicited|unknown|stranger|officer|police|cbi|customs|recruiter|hr |agent|claiming|group admin|call from|video call|link"
pct = lambda xs: round(100 * sum(xs) / len(xs), 1) if xs else None


def agent_behaviour():
    recs = [json.loads(l) for l in open(EPISODES, encoding="utf-8")]
    cases = {c.case_id: c for c in load_cases(CARDS, "test")}
    seqs = collections.Counter(" > ".join(t["tool"] or "?" for t in r["turns"]) for r in recs)
    top5 = sum(n for _, n in seqs.most_common(5))
    amb = [r for r in recs if r["clarity"] == "ambiguous"]
    by = collections.defaultdict(list)
    for r in amb:
        c = cases[r["case_id"]]; amt = c.task["amount"]; flagged = any(flags_from_signals(c.signals).values())
        band = "under Rs 20,000" if amt < 20_000 else "Rs 20,000 to 50,000" if amt <= 50_000 else "over Rs 50,000"
        by[("amount", band, r["variant"])].append(r["asked"]); by[("checks", "any flag" if flagged else "no flag", r["variant"])].append(r["asked"])
    qs = [t["args"].get("question", "") for r in recs if r["lang"] == "en" for t in r["turns"] if t["tool"] == "ask_customer"]
    who = [bool(re.search(r"who (asked|told|contacted)|how did (they|you get|you come|this person)|contact(ed)? you", q, re.I)) for q in qs]
    return {"episodes": len(recs), "distinct_tool_sequences": len(seqs), "top5_sequences_share_pct": round(100 * top5 / len(recs), 1),
            "top5_sequences": seqs.most_common(5), "max_questions_in_an_episode": max(r["n_questions"] for r in recs),
            "ambiguous_questioned_pct": {v: pct([r["asked"] for r in amb if r["variant"] == v]) for v in ("genuine", "scam")},
            "ambiguous_questioned_by": {f"{k[0]}: {k[1]} ({k[2]})": {"pct": pct(v), "n": len(v)} for k, v in sorted(by.items())},
            "en_questions": len(qs), "en_questions_about_who_or_how_contacted_pct": pct(who)}


def keyword_rule():
    cards = [json.loads(l) for l in open(CARDS, encoding="utf-8")]
    out = {}
    for split in ("train", "test"):
        en = [c for c in cards if c["lang"] == "en" and c["split"] == split]
        hit = lambda a: bool(re.search(KEYWORDS, a["who_asked"] + " " + a["how_contacted"], re.I))
        out[split] = {"cards": len(en), "scams_caught_pct": pct([hit(c["card"]["scam_answers"]) for c in en]),
                      "genuine_flagged_pct": pct([hit(c["card"]["genuine_answers"]) for c in en])}
    en = [c for c in cards if c["lang"] == "en"]
    out["secret_yes_pct"] = {"scam": pct([c["card"]["scam_answers"]["told_to_keep_secret"].strip().lower().startswith("yes") for c in en]),
                             "genuine": pct([c["card"]["genuine_answers"]["told_to_keep_secret"].strip().lower().startswith("yes") for c in en])}
    out["keywords"] = KEYWORDS
    return out


def simulator():
    r = json.load(open(RULE1)); runs = r["runs"]
    keep = {k: {x: runs[k][x] for x in ("u", "closure", "scam_paid", "gen_held", "gen_no_form", "fields_gen", "lookups")} for k in runs}
    return {"generator_hash": r["hash"], "held_out_worlds": r["n_held"], "runs": keep, "checks": r["checks"]}


if __name__ == "__main__":
    res = {"v3_agent": agent_behaviour(), "v3_cards_keyword_rule": keyword_rule(), "v4_simulator": simulator()}
    os.makedirs(os.path.join(ROOT, "results/bankdesk_v4"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "results/bankdesk_v4/ARTICLE_NUMBERS.json"), "w"), indent=1, default=str)
    a, k, s = res["v3_agent"], res["v3_cards_keyword_rule"], res["v4_simulator"]
    L = ["# Numbers for article section 7.10", "", f"GRPO3, test split ({a['episodes']} episodes, `{os.path.relpath(EPISODES, ROOT)}`):",
         f"- {a['distinct_tool_sequences']} distinct tool sequences; the five most common cover {a['top5_sequences_share_pct']}%.",
         f"- At most {a['max_questions_in_an_episode']} questions in any episode.",
         f"- Ambiguous cases questioned: genuine {a['ambiguous_questioned_pct']['genuine']}%, scam {a['ambiguous_questioned_pct']['scam']}%.",
         f"- English questions about who asked or how they were contacted: {a['en_questions_about_who_or_how_contacted_pct']}% of {a['en_questions']}.",
         "", "| ambiguous cases | questioned % | n |", "|---|---|---|"]
    L += [f"| {key} | {v['pct']} | {v['n']} |" for key, v in a["ambiguous_questioned_by"].items()]
    L += ["", "Keyword rule on the scam victim's two answers (who asked, how contacted), English cards:",
          f"- train ({k['train']['cards']} cards): scams caught {k['train']['scams_caught_pct']}%, genuine flagged {k['train']['genuine_flagged_pct']}%",
          f"- test ({k['test']['cards']} cards): scams caught {k['test']['scams_caught_pct']}%, genuine flagged {k['test']['genuine_flagged_pct']}%",
          f"- 'told to keep it secret: yes': scam {k['secret_yes_pct']['scam']}%, genuine {k['secret_yes_pct']['genuine']}%",
          "", f"v4 simulator (generator `{s['generator_hash']}`, {s['held_out_worlds']} held-out worlds): see `results/bankdesk_v4/RULE1.md`."]
    open(os.path.join(ROOT, "results/bankdesk_v4/ARTICLE_NUMBERS.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
