"""Train/test leak check, as pre-declared in PLAN.md (RULE LEAK-1, 2026-11-16 14:58 IST). CPU only, no network.

Every eval prompt is compared with every training prompt after normalising (Unicode NFKC, lowercase, punctuation
turned into spaces, whitespace collapsed). Exact match: equal normalised strings. Near match: character 5-gram Jaccard
>= 0.8 (exact matches count as near matches too). Pairs:
  (a) SFT user turns against each chat eval set, per language;
  (b) SafeGrad refusal prompts (refusals_train.jsonl, and the AdvBench parquet it came from) against HarmBench and
      XSTest-unsafe;
  (c) BankDesk card openings (ambiguous, clear-scam and clear-genuine) of train, dev, dev2 and RL cards against the
      111 v3 test cards and the 273 test2 cards. A test card matches if any of its openings matches any training opening.
Harmful sets are reported by id and count only; no harmful prompt text is written. RBI text is not written either (RBI
FAQ text stays out of git).

Run from anywhere: python3 -I scripts/leak_check.py
Writes results/LEAK_CHECK.md and results/LEAK_CHECK.json.
"""
import hashlib, json, re, unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OUT_MD, OUT_JSON = ROOT / "results" / "LEAK_CHECK.md", ROOT / "results" / "LEAK_CHECK.json"
K, THRESH = 5, 0.8
HARMFUL = {"bank_redteam", "harmbench", "xstest_unsafe"}  # ids only, never text
NO_TEXT = HARMFUL | {"rbi_qa"}  # RBI: licence, text stays out of git
CHAT_SETS = ["bank_task", "bank_redteam", "bank_borderline", "scam_victim", "genuine_urgent", "rbi_qa",
             "xstest_safe", "xstest_unsafe", "harmbench"]
OPENING_FIELDS = ("opening", "clear_scam_opening", "clear_genuine_opening")


def norm(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = "".join(" " if unicodedata.category(ch).startswith("P") else ch for ch in t)
    return re.sub(r"\s+", " ", t).strip()


def shingles(t):
    return {t[i:i + K] for i in range(len(t) - K + 1)} if len(t) >= K else ({t} if t else set())


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def item(iid, texts, lang=None, **extra):
    """One unit being compared: an id and one or more texts (a card has three openings)."""
    return {"id": iid, "texts": [(f, norm(t)) for f, t in texts if t and norm(t)],
            "raw": {f: t for f, t in texts if t}, "lang": lang, **extra}


def jaccard_matrix(a_texts, b_texts):
    """Dense Jaccard between two lists of normalised strings via binary sparse 5-gram matrices."""
    vocab, rows = {}, []
    for t in a_texts + b_texts:
        rows.append([vocab.setdefault(s, len(vocab)) for s in shingles(t)])

    def mat(rs):
        indptr = np.cumsum([0] + [len(r) for r in rs])
        idx = np.fromiter((c for r in rs for c in r), dtype=np.int64, count=int(indptr[-1]))
        return sparse.csr_matrix((np.ones(len(idx), dtype=np.int32), idx, indptr), shape=(len(rs), len(vocab)))
    A, B = mat(rows[:len(a_texts)]), mat(rows[len(a_texts):])
    inter = (A @ B.T).toarray().astype(np.float64)
    na, nb = np.asarray(A.sum(1)).ravel(), np.asarray(B.sum(1)).ravel()
    union = na[:, None] + nb[None, :] - inter
    return np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)


def compare(eval_items, train_items):
    """Per eval unit: exact match?, best Jaccard, the train unit and fields behind it, all near-matching train ids."""
    ef = [(i, f, t) for i, it in enumerate(eval_items) for f, t in it["texts"]]
    tf = [(j, f, t) for j, it in enumerate(train_items) for f, t in it["texts"]]
    J = jaccard_matrix([t for _, _, t in ef], [t for _, _, t in tf])
    exact_index = {}
    for c, (j, _, t) in enumerate(tf):
        exact_index.setdefault(t, []).append(c)
    e_owner = np.array([i for i, _, _ in ef]); t_owner = np.array([j for j, _, _ in tf])
    out = []
    for i, it in enumerate(eval_items):
        rows = np.where(e_owner == i)[0]
        if len(rows) == 0:
            out.append({"exact": False, "best_j": 0.0, "near_train": []}); continue
        sub = J[rows]
        r, c = np.unravel_index(int(np.argmax(sub)), sub.shape)
        exact_cols = [c2 for row in rows for c2 in exact_index.get(ef[row][2], [])]
        near_cols = sorted(set(np.where((sub >= THRESH).any(0))[0].tolist()) | set(exact_cols))
        out.append({"exact": bool(exact_cols), "best_j": float(sub[r, c]),
                    "best_train": train_items[t_owner[c]]["id"], "best_eval_field": ef[rows[r]][1],
                    "best_train_field": tf[c][1], "best_pair_raw": (it["raw"].get(ef[rows[r]][1], ""),
                                                                    train_items[t_owner[c]]["raw"].get(tf[c][1], "")),
                    "near_train": sorted({train_items[t_owner[c2]]["id"] for c2 in near_cols})})
    return out


def within_set(items):
    """Duplicate pairs inside one set (upper triangle)."""
    texts = [it["texts"][0][1] for it in items]
    J = jaccard_matrix(texts, texts)
    iu = np.triu_indices(len(texts), 1)
    exact = [(a, b) for a, b in zip(*iu) if texts[a] == texts[b]]
    near = [(a, b) for a, b in zip(*iu) if J[a, b] >= THRESH or texts[a] == texts[b]]
    return {"n": len(items), "exact_pairs": len(exact), "near_pairs": len(near),
            "items_in_exact_pair": len({x for p in exact for x in p}),
            "items_in_near_pair": len({x for p in near for x in p}),
            "examples": [(items[a]["id"], items[a]["raw"]["prompt"][:100], items[b]["id"], items[b]["raw"]["prompt"][:100],
                          round(float(J[a, b]), 3)) for a, b in near[:3]]}


def main():
    files, rows, examples = {}, [], {}

    # ---- training sources
    sft_p = D / "sft_raw.jsonl"; files["sft"] = sft_p
    sft = [item(f"sft_raw#{i}", [("user", r["messages"][0]["content"])], r["meta"].get("lang"))
           for i, r in enumerate(jsonl(sft_p)) if r["messages"][0]["role"] == "user"]
    ref_p = D / "refusals_train.jsonl"; files["refusals"] = ref_p
    refusals = [item(f"refusals_train#{i}", [("prompt", r["prompt"])], r["lang"]) for i, r in enumerate(jsonl(ref_p))]
    adv_p = D / "upload" / "advbench" / "advbench_train_prompts.parquet"; files["advbench"] = adv_p
    adv = [item(f"advbench#{r.id}", [("prompt", r.prompt)], "en") for r in pd.read_parquet(adv_p).itertuples()]

    cards_v3_p, dev2_p, rl_p, test2_p = (D / "bankdesk" / f for f in
                                         ("cards_v3.jsonl", "cards_dev2.jsonl", "cards_rl_all.jsonl", "cards_test2.jsonl"))
    files.update(cards_v3=cards_v3_p, cards_dev2=dev2_p, cards_rl_all=rl_p, cards_test2=test2_p)

    def cards(p, split=None):
        return [item(c["card_id"], [(f, c["card"].get(f, "")) for f in OPENING_FIELDS], c["lang"])
                for c in jsonl(p) if split is None or c["split"] == split]
    card_src = {"v3 train": cards(cards_v3_p, "train"), "v3 dev": cards(cards_v3_p, "dev"),
                "dev2": cards(dev2_p), "rl_all": cards(rl_p)}
    card_src["all train+dev+dev2+rl"] = [c for v in card_src.values() for c in v]
    card_test = {"v3 test (111)": cards(cards_v3_p, "test"), "test2 (273)": cards(test2_p)}

    # ---- eval sets
    chat = {}
    for s in CHAT_SETS:
        for lang in ("en", "hi"):
            p = D / "eval" / f"{s}_{lang}.jsonl"
            if not p.exists():
                rows.append({"section": "a", "train": "SFT user turns", "eval": s, "lang": lang, "missing": str(p)}); continue
            files[f"{s}_{lang}"] = p
            chat[(s, lang)] = [item(r["id"], [("prompt", r["prompt"])], lang, set=s) for r in jsonl(p)]

    def record(section, train_name, train_items, eval_name, lang, ev, show_text):
        res = compare(ev, train_items)
        near = [(it, r) for it, r in zip(ev, res) if r["exact"] or r["best_j"] >= THRESH]
        row = {"section": section, "train": train_name, "n_train": len(train_items), "eval": eval_name, "lang": lang,
               "n_eval": len(ev), "exact": sum(r["exact"] for r in res), "near": len(near),
               "share_near_pct": round(100 * len(near) / len(ev), 2) if ev else None,
               "max_j": round(max((r["best_j"] for r in res), default=0.0), 3),
               "matches": [{"eval_id": it["id"], "exact": r["exact"], "best_j": round(r["best_j"], 3),
                            "best_train_id": r["best_train"], "eval_field": r["best_eval_field"],
                            "train_field": r["best_train_field"], "near_train_ids": r["near_train"]} for it, r in near]}
        if show_text and near:
            examples[(section, train_name, eval_name, lang)] = [
                (it["id"], r["best_pair_raw"][0][:100], r["best_train"], r["best_pair_raw"][1][:100], round(r["best_j"], 3))
                for it, r in sorted(near, key=lambda x: -x[1]["best_j"])[:3]]
        rows.append(row)

    # (a) SFT user turns vs chat eval sets
    for (s, lang), ev in chat.items():
        record("a", "SFT user turns", sft, s, lang, ev, s not in NO_TEXT)
    # (b) SafeGrad refusal prompts vs HarmBench and XSTest-unsafe (harmful: ids only)
    for tname, titems in (("SafeGrad refusals_train", refusals), ("AdvBench parquet (424)", adv)):
        for s in ("harmbench", "xstest_unsafe"):
            for lang in ("en", "hi"):
                if (s, lang) in chat:
                    record("b", tname, titems, s, lang, chat[(s, lang)], False)
    # (c) BankDesk card openings
    for tname, titems in card_src.items():
        for ename, eitems in card_test.items():
            for lang in ("en", "hi"):
                record("c", f"cards {tname}", titems, ename, lang, [c for c in eitems if c["lang"] == lang], True)

    within = {lang: within_set(chat[("bank_task", lang)]) for lang in ("en", "hi") if ("bank_task", lang) in chat}

    # ---- write JSON
    OUT_JSON.parent.mkdir(exist_ok=True)
    json.dump({"rule": "LEAK-1 (PLAN.md, 2026-11-16 14:58 IST)", "k": K, "near_threshold": THRESH,
               "normalisation": "NFKC, lowercase, Unicode punctuation (category P*) -> space, whitespace collapsed",
               "note_sft_source": "data/sft_raw.jsonl (2,992 rows) is the pre-CuratorKIT file; the 2,985-row kept file "
                                  "(sft_sharegpt.jsonl) is not in this checkout. Counts for (a) are an upper bound.",
               "files": {k: {"path": str(Path(v).relative_to(ROOT)), "md5": md5(v)} for k, v in files.items()},
               "rows": rows, "within_set_bank_task": within},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- write markdown
    L = ["# Train/test leak check (RULE LEAK-1)", "",
         f"Script: `scripts/leak_check.py` (run: `python3 -I scripts/leak_check.py`). CPU only, no network.",
         f"Normalisation: Unicode NFKC, lowercase, punctuation to space, whitespace collapsed. Exact = equal normalised "
         f"strings. Near = character {K}-gram Jaccard >= {THRESH} (exact matches are included in the near count). "
         f"Share = near / eval set size. Rows over 1% are marked **yes**.", "",
         "SFT source: `data/sft_raw.jsonl`, 2,992 user turns. The 2,985-row CuratorKIT output (`sft_sharegpt.jsonl`) "
         "is not in this checkout, so section (a) checks the 2,992-row file it was cut from. Every kept row is in it, "
         "so (a) counts are an upper bound (at most 7 extra rows).", "",
         "BankDesk: each card has three openings (ambiguous, clear scam, clear genuine). A test card counts as matched "
         "if any of its openings matches any opening of a training card.", ""]
    ok = [r for r in rows if "missing" not in r]
    over = [r for r in ok if r["share_near_pct"] > 1]
    zero = sum(r["near"] == 0 for r in ok)
    max_bc = max(r["max_j"] for r in ok if r["section"] in "bc")
    max_harm_a = max(r["max_j"] for r in ok if r["section"] == "a" and r["eval"] in HARMFUL)
    summ = [f"{len(ok)} rows checked; {zero} have no near match."]
    summ.append("Over 1% near matches: " + "; ".join(
        f"{r['train']} vs {r['eval']} {r['lang']}, {r['near']} of {r['n_eval']} ({r['share_near_pct']:.1f}%), "
        f"{r['exact']} exact" for r in over) + "." if over else "No row is over 1% near matches.")
    if not any(r["near"] for r in ok if r["section"] in "bc" or r["eval"] in HARMFUL):
        summ.append(f"Harmful sets, refusal prompts and BankDesk cards have no near match: the highest Jaccard is "
                    f"{max_harm_a:.2f} between SFT turns and any harmful set, and {max_bc:.2f} in sections (b) and (c).")
    if all(r["eval"] == "bank_task" for r in ok if r["near"]):
        summ.append("Every match found is a short Banking77 query; a near match on a short query is not always the "
                    "same question (see the examples).")
    L += ["## What it shows", "", " ".join(summ), ""]
    sec_title = {"a": "(a) SFT user turns against chat eval sets",
                 "b": "(b) SafeGrad refusal prompts against HarmBench and XSTest-unsafe (ids only)",
                 "c": "(c) BankDesk card openings against test cards"}
    for sec in ("a", "b", "c"):
        L += [f"## {sec_title[sec]}", "", "| train source | eval set | lang | eval n | exact | near (J>=0.8) | near % | max J | >1% |",
              "|---|---|---|---:|---:|---:|---:|---:|---|"]
        for r in rows:
            if r["section"] != sec:
                continue
            if "missing" in r:
                L.append(f"| {r['train']} | {r['eval']} | {r['lang']} | missing: `{r['missing']}` | | | | | |"); continue
            flag = "**yes**" if r["share_near_pct"] and r["share_near_pct"] > 1 else "no"
            L.append(f"| {r['train']} ({r['n_train']}) | {r['eval']} | {r['lang']} | {r['n_eval']} | {r['exact']} | "
                     f"{r['near']} | {r['share_near_pct']:.1f} | {r['max_j']:.2f} | {flag} |")
        L.append("")
    L += ["## Within-set duplicates: bank task (Banking77 test queries)", "",
          "| lang | n | exact pairs | near pairs | items in an exact pair | items in a near pair |", "|---|---:|---:|---:|---:|---:|"]
    for lang, w in within.items():
        L.append(f"| {lang} | {w['n']} | {w['exact_pairs']} | {w['near_pairs']} | {w['items_in_exact_pair']} | {w['items_in_near_pair']} |")
    L.append("")
    L += ["## Near-match ids", "", "Harmful and RBI sets: eval id -> best training id, Jaccard. No text.", ""]
    if not any(r.get("matches") and r["eval"] in NO_TEXT for r in rows):
        L.append("- None: no harmful or RBI eval prompt has a near match.")
    for r in rows:
        if r.get("matches") and r["eval"] in NO_TEXT:
            ids = ", ".join(f"{m['eval_id']} -> {m['best_train_id']} ({m['best_j']:.2f}{', exact' if m['exact'] else ''})"
                            for m in r["matches"])
            L.append(f"- {r['train']} vs {r['eval']} {r['lang']}: {ids}")
    L += ["", "## Examples (benign sets only, up to 3 per row, 100 characters each)", ""]
    for (sec, tname, ename, lang), ex in examples.items():
        L.append(f"**{tname} vs {ename} {lang}**")
        for eid, et, tid, tt, j in ex:
            L.append(f"- J={j:.2f} eval `{eid}`: {et!r} / train `{tid}`: {tt!r}")
        L.append("")
    for lang, w in within.items():
        if w["examples"]:
            L.append(f"**bank task {lang}, within-set pairs**")
            for a, at, b, bt, j in w["examples"]:
                L.append(f"- J={j:.2f} `{a}`: {at!r} / `{b}`: {bt!r}")
            L.append("")
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    for r in rows:
        if "missing" in r:
            print("MISSING", r); continue
        print(f"{r['section']} | {r['train']:<32} | {r['eval']:<16} | {r['lang']} | n={r['n_eval']:<4} exact={r['exact']:<3} "
              f"near={r['near']:<3} {r['share_near_pct']:.1f}% maxJ={r['max_j']:.2f}")
    print("within bank_task:", {k: {kk: vv for kk, vv in v.items() if kk != 'examples'} for k, v in within.items()})
    print("wrote", OUT_MD, OUT_JSON)


if __name__ == "__main__":
    main()
