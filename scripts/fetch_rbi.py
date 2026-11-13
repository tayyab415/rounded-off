#!/usr/bin/env python3
"""Build an EN/HI Q&A set from RBI's public FAQ pages (rbi.org.in/commonman).

One command reproduces everything from scratch:

    python3 scripts/fetch_rbi.py

Stages: list sections -> fetch FAQ documents -> parse Q&A -> pair EN/HI ->
write data/rbi/*.jsonl, STATS.md, TERMS.md. Direct HTTP only, one request per
second, every page cached under data/raw/rbi_html/ so reruns do not refetch.
Fetched HTML is treated as data: it is only parsed, never executed.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "rbi_html"
OUT = ROOT / "data" / "rbi"

BASE = "https://www.rbi.org.in/commonman/{lang}/Scripts/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MIN_GAP = 1.1  # seconds between network requests

# Retail-banking sections requested. SID -> topic name used in the output.
SECTIONS = {
    8: "Banking",
    23: "Payment Systems",
    32: "Consumer Education and Protection",
    35: "FinTech",
    9: "Currency",
    30: "Financial Inclusion and Development",
    34: "Deposit Insurance and Credit Guarantee Corporation",
}
LANGS = {"en": "English", "hi": "Hindi"}


class Blocked(RuntimeError):
    pass


_last_request = 0.0
_net_requests = 0


def fetch(url, cache_name):
    """Return HTML text for url, using the on-disk cache when present."""
    global _last_request, _net_requests
    path = CACHE / cache_name
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes().decode("utf-8", errors="replace")
    CACHE.mkdir(parents=True, exist_ok=True)
    wait = MIN_GAP - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9"})
    for attempt in range(3):
        _last_request = time.monotonic()
        _net_requests += 1
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise Blocked(f"HTTP {e.code} for {url}: site is blocking us; stopping")
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    path.write_bytes(raw)
    return raw.decode("utf-8", errors="replace")


def section_url(lang, sid):
    return BASE.format(lang=LANGS[lang]) + f"FAQs.aspx?SID={sid}"


def doc_url(lang, doc_id):
    return BASE.format(lang=LANGS[lang]) + f"FAQs.aspx?Id={doc_id}"


# ---------------------------------------------------------------- listing

TAG_RE = re.compile(r"<[^>]+>")


def to_text(fragment):
    """HTML fragment -> single-line text (entities decoded, whitespace folded)."""
    t = TAG_RE.sub(" ", fragment)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def parse_listing(page):
    """Return [(doc_id, title)] from a section index page."""
    i = page.find('id="lblData"')
    body = page[i:] if i >= 0 else page
    out = []
    for m in re.finditer(r"<a[^>]*href=['\"]?FAQs\.aspx\?Id=(\d+)[^>]*>(.*?)</a>", body, re.S | re.I):
        title = to_text(m.group(2))
        out.append((int(m.group(1)), title))
    return out


# ---------------------------------------------------------------- document -> lines

from bs4 import BeautifulSoup, NavigableString, Tag  # noqa: E402

BLOCK = {"p", "div", "ol", "ul", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
         "center", "pre", "dl", "dt", "dd", "section", "article"}
SKIP = {"script", "style", "noscript"}


def _flat(node):
    return re.sub(r"\s+", " ", node.get_text(" ")).replace("\xa0", " ").strip()


def _layout_table(tbl):
    """True if every row has one cell (a layout wrapper, not a data table)."""
    rows = tbl.find_all("tr", recursive=False) or [
        r for tb in tbl.find_all("tbody", recursive=False) for r in tb.find_all("tr", recursive=False)]
    if not rows:
        return True
    return all(len(r.find_all(["td", "th"], recursive=False)) <= 1 for r in rows)


def doc_lines(root):
    """Walk an element and return readable text lines.

    List items become '- ' lines; data-table rows become 'a | b | c' lines;
    single-column layout tables are walked through.
    """
    out, buf, bullet = [], [], []

    def flush():
        t = re.sub(r"\s+", " ", "".join(buf)).replace("\xa0", " ").strip()
        buf.clear()
        if t:
            out.append(("- " if bullet else "") + t)
            bullet.clear()

    def walk(n, depth=0):
        for c in n.children:
            if isinstance(c, NavigableString):
                if not isinstance(c, type(c)) or c.__class__.__name__ in ("Comment", "Doctype"):
                    continue
                buf.append(str(c))
            elif isinstance(c, Tag):
                nm = c.name.lower()
                if nm in SKIP:
                    continue
                if nm == "br":
                    flush()
                elif nm == "li":
                    flush()
                    bullet[:] = [1]            # the next text line gets the "- " marker
                    walk(c, depth + 1)
                    flush()
                    bullet.clear()
                elif nm == "table":
                    flush()
                    if _layout_table(c):
                        walk(c, depth)
                    else:
                        for tr in c.find_all("tr"):
                            if tr.find_parent("table") is not c:
                                continue
                            cells = [_flat(td) for td in tr.find_all(["td", "th"], recursive=False)]
                            if any(cells):
                                out.append(" | ".join(cells))
                elif nm in BLOCK or nm in ("tr", "td", "th", "tbody", "thead", "tfoot"):
                    flush()
                    walk(c, depth)
                    flush()
                else:
                    walk(c, depth)

    walk(root)
    flush()
    return out


def parse_doc_page(page):
    """Return (title, date, lines) for a FAQs.aspx?Id=n page, or None if empty."""
    soup = BeautifulSoup(page, "lxml")
    pr = soup.find(id="prData")
    if pr is None:
        return None
    head = soup.find("td", class_="textIndexHead")
    title = _flat(head) if head else ""
    d = soup.find(string=re.compile(r"Date:"))
    date = ""
    if d is not None:
        m = re.search(r"(\d{2}/\d{2}/\d{4})", _flat(d.parent.parent if d.parent else d))
        date = m.group(1) if m else ""
    content = pr.find("td", class_="textDetails") or pr
    return title, date, doc_lines(content)


# ---------------------------------------------------------------- Q&A extraction

import unicodedata  # noqa: E402

# "Q 1." / "Q1." / "Q.1." / "प्रश्न 1." / "प्र.1." / "1." / "1)"; bare numbers need a delimiter.
Q_RE = re.compile(
    r"^(?:(?:Q(?:uestion)?|प्रश्न|प्र)\s*\.?\s*(?P<a>\d{1,3})\s*[\.\):\-]?"
    r"|(?P<b>\d{1,3})\s*[\.\)]"
    r"|(?P<c>\d{1,3})\s+(?=(?:प्रश्न|Query|Question)\s*:))\s*(?P<text>.*)$", re.S)
TABLE_Q_RE = re.compile(r"^(\d{1,3})\s*\|\s*(.+?)\s*\|\s*(.+)$", re.S)
ANS_PREFIX_RE = re.compile(
    r"^(?:Ans(?:wer)?|Response|Clarification|उत्तर|उ)\s*[\.:\-\u0903]\s*", re.I)
QUERY_PREFIX_RE = re.compile(r"^(?:Query|Question|प्रश्न)\s*\d*\s*[:\.\-]\s*", re.I)
INLINE_ANS_RE = re.compile(r"\s(?:Clarification|उत्तर)\s*[:\u0903]")


BOILERPLATE_RE = re.compile(
    r"^(?:Disclaimer\s*:\s*)?These FAQs are (?:issued|for information)|^Notice\s*:\s*Information given above|"
    r"^All You wanted to know from RBI|^(?:दावा-अस्वीकरण\s*:\s*)?ये (?:अक्सर पूछे जाने वाले प्रश्न|आम जानकारी|सामान्य प्रश्न)|"
    r"^नोटिस\s*:\s*ऊपर दी गई जानकारी|^भारतीय रिजर्व बैंक से आप .* जानना चाहते हैं")


def _texty(q):
    letters = sum(1 for ch in q if ch.isalpha() or unicodedata.category(ch).startswith("M"))
    return letters >= 6 and letters / max(len(q), 1) >= 0.5


def clean_line(t):
    t = unicodedata.normalize("NFC", t)
    t = t.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    return re.sub(r"[ \t\xa0]+", " ", t).strip()


def looks_like_heading(line):
    """A short unpunctuated line, 'A. Basics', or 'II. DEPOSITS' sitting between FAQs."""
    if line.startswith("- ") or "|" in line or re.search(r"https?://|->|[<>]|\.pdf", line, re.I):
        return False
    if re.match(r"^(?:[A-Z]|[IVX]{1,4})\s*[\.\)]\s+\S", line) and len(line) < 160:
        return True
    return len(line) < 90 and not re.search(r"[\.;:?!\)\u0964]$", line)


def parse_qa(lines, rejected=None, trimmed=None):
    """Split document lines into [(num, question, answer_lines)].

    Question markers must follow the running sequence 1, 2, 3, ... so numbered
    list items inside an answer are not mistaken for new questions. A restart
    at 1 is accepted when the line before it is a section heading.
    """
    items = []
    cur = None
    last = 0
    prev_line = ""
    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue
        if line.startswith("|"):          # empty-first-cell table row = section heading row
            continue
        num = q = a_inline = None
        m = TABLE_Q_RE.match(line)
        if m and _texty(m.group(2)) and m.group(2).rstrip().endswith("?"):   # a table of questions, not data rows
            num, q, a_inline = int(m.group(1)), m.group(2), m.group(3)
        else:
            m = Q_RE.match(line)
            if m:
                num = int(m.group("a") or m.group("b") or m.group("c"))
                q = m.group("text").strip()
        ok = False
        if num is not None:
            if num == last + 1:
                ok = True
            elif num == 1 and last > 1 and a_inline is None and looks_like_heading(prev_line):
                ok = True
        if ok:
            q = q.lstrip("| ").strip()
            q = QUERY_PREFIX_RE.sub("", q)
            inline_ans = a_inline
            if inline_ans is None:
                parts = INLINE_ANS_RE.split(q, maxsplit=1)
                if len(parts) == 2:
                    q, inline_ans = parts
            cur = {"num": num, "q": q.strip(), "a": [inline_ans.strip()] if inline_ans else [], "q_open": not q.strip()}
            items.append(cur)
            last = num
        elif cur is not None:
            if num is not None and rejected is not None and q and q.rstrip().endswith(("?", "?")):
                rejected.append(f"{num}: {q[:80]}")
            if cur["q_open"]:
                cur["q"] = line
                cur["q_open"] = False
            else:
                cur["a"].append(line)
        prev_line = line
    out = []
    for it in items:
        a = it["a"]
        # drop a trailing section heading that belongs to the next block
        while a and looks_like_heading(a[-1]) and len(a) > 1 and it is not items[-1]:
            if trimmed is not None:
                trimmed.append(a[-1])
            a = a[:-1]
        if it is items[-1]:                # page footer notes after the last answer
            while a and BOILERPLATE_RE.match(a[-1]):
                if trimmed is not None:
                    trimmed.append("[footer] " + a[-1][:60])
                a = a[:-1]
        if a:
            a = [ANS_PREFIX_RE.sub("", a[0], count=1)] + a[1:]
            a = [x for x in a if x]
        out.append((it["num"], it["q"], a))
    return out


# ---------------------------------------------------------------- build rows

# Documents deliberately left out. Reason is written to STATS.md.
EXCLUDE_DOCS = {
    1169: "Licensing of new private-sector banks: not retail banking; the questions are listed "
          "first and answered in grouped blocks ('A.(1 to 4) ...'), so Q/A pairs cannot be matched.",
}
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def deva_ratio(text):
    letters = [c for c in text if c.isalpha() or unicodedata.category(c).startswith("M")]
    if not letters:
        return 0.0
    return sum(1 for c in letters if DEVANAGARI_RE.match(c)) / len(letters)


def iso_date(ddmmyyyy):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", ddmmyyyy or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def cache_date(name):
    return dt.datetime.fromtimestamp((CACHE / name).stat().st_mtime).date().isoformat()


def collect_listings():
    """{lang: {doc_id: {'title': str, 'sids': [sid, ...]}}}, in SECTIONS order."""
    out = {l: {} for l in LANGS}
    for lang in LANGS:
        for sid in SECTIONS:
            page = fetch(section_url(lang, sid), f"{lang}_SID{sid}.html")
            for doc_id, title in parse_listing(page):
                d = out[lang].setdefault(doc_id, {"title": title, "sids": []})
                if sid not in d["sids"]:
                    d["sids"].append(sid)
    return out


def primary_section(sids):
    for sid in SECTIONS:
        if sid in sids:
            return SECTIONS[sid]
    return None


def build_rows(listings):
    rows, doc_report = [], []
    en_ids = set(listings["en"])
    for lang in LANGS:
        for doc_id in sorted(listings[lang]):
            name = f"{lang}_Id{doc_id}.html"
            page = fetch(doc_url(lang, doc_id), name)
            rep = {"lang": lang, "doc_id": doc_id, "listing_title": listings[lang][doc_id]["title"],
                   "status": "ok", "parsed": 0, "kept": 0}
            if doc_id in EXCLUDE_DOCS:
                rep["status"] = "excluded: " + EXCLUDE_DOCS[doc_id]
                doc_report.append(rep)
                continue
            parsed = parse_doc_page(page)
            if parsed is None or not parsed[2]:
                rep["status"] = "empty page (content is a PDF link only)"
                doc_report.append(rep)
                continue
            title, date, lines = parsed
            rejected, trimmed = [], []
            qa = parse_qa(lines, rejected, trimmed)
            rep["trimmed"] = trimmed
            rep["parsed"] = len(qa)
            rep["rejected_question_like"] = rejected
            if lang == "hi":
                sample = " ".join(q + " " + " ".join(a) for _, q, a in qa)
                if deva_ratio(sample) < 0.3:
                    rep["status"] = "excluded: body is in a legacy Hindi font (Latin glyphs, not Unicode)"
                    doc_report.append(rep)
                    continue
            title_lang = lang
            if lang == "hi" and title and not DEVANAGARI_RE.search(title):
                en_title = re.sub(r"^[A-Z][a-z]{2} \d{1,2}, \d{4} - ", "", listings["en"].get(doc_id, {}).get("title", ""))
                rep["title_note"] = f"Hindi title has no Devanagari (legacy-font text) ({title!r}); used English title"
                title, title_lang = en_title or title, "en"
            sids = sorted(set(listings[lang][doc_id]["sids"]) | set(
                listings["en"].get(doc_id, {}).get("sids", [])), key=list(SECTIONS).index)
            section = primary_section(sids)
            for idx, (num, q, a) in enumerate(qa, start=1):
                answer = "\n".join(a).strip()
                if not q.strip() or not answer:
                    continue
                row = {
                    "id": f"rbi-{lang}-{doc_id}-{idx}",
                    "lang": lang,
                    "section": section,
                    "doc_title": title,
                    "question": q.strip(),
                    "answer": answer,
                    "source_url": doc_url(lang, doc_id),
                    "retrieved_at": cache_date(name),
                    "pair_id": None,
                    "answer_chars": len(answer),
                    "doc_id": doc_id,
                    "doc_date": iso_date(date),
                    "q_num": num,
                    "doc_title_lang": title_lang,
                }
                if len(sids) > 1:
                    row["also_in_sections"] = [SECTIONS[x] for x in sids if SECTIONS[x] != section]
                rows.append(row)
                rep["kept"] += 1
            doc_report.append(rep)
    return rows, doc_report


def signature(text):
    """Numbers in a row, with URLs/emails removed (Hindi pages link to Hindi URLs)."""
    t = re.sub(r"https?://\S+|www\.\S+|\b[\w.-]+@[\w.-]+\b|\S+\.(?:pdf|docx?|xlsx?)\b|\b[A-Z0-9]{12,}\b", " ", text, flags=re.I)
    t = t.translate(str.maketrans("\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f", "0123456789"))
    nums = {x.replace(",", "").rstrip(".") for x in re.findall(r"\d[\d,]*\.?\d*", t)}
    return nums


def pair_rows(rows):
    """Pair EN/HI rows with the same doc id and position when the two docs line up.

    A doc pair is matched only if both languages have the same number of questions.
    Each row pair must also share at least one number (translations keep them); doc pairs
    where more than 10% (and more than one) of the number-bearing rows disagree are left unpaired.
    Returns {doc_id: {"en": n, "hi": n, "paired": n, "note": str}}.
    """
    by = defaultdict(lambda: {"en": {}, "hi": {}})
    for r in rows:
        by[r["doc_id"]][r["lang"]][int(r["id"].rsplit("-", 1)[1])] = r
    report = {}
    for doc_id, d in sorted(by.items()):
        en, hi = d["en"], d["hi"]
        info = {"en": len(en), "hi": len(hi), "paired": 0, "note": ""}
        report[doc_id] = info
        if not en or not hi:
            info["note"] = "only one language available"
            continue
        if set(en) != set(hi):
            info["note"] = "question counts differ (EN/HI are different revisions): not paired"
            continue
        checks, fails = [], 0
        for pos in sorted(en):
            se = signature(en[pos]["question"] + " " + en[pos]["answer"])
            sh = signature(hi[pos]["question"] + " " + hi[pos]["answer"])
            if not se and not sh:
                checks.append((pos, True, False))
                continue
            ok = bool(se & sh) if (se and sh) else (len(se | sh) <= 2)
            checks.append((pos, ok, True))
            fails += (not ok)
        tokenful = sum(1 for _, _, t in checks if t)
        if tokenful and fails > max(1, 0.10 * tokenful):
            info["note"] = f"number check failed on {fails}/{tokenful} rows: not paired"
            continue
        for pos, ok, _ in checks:
            if ok:
                pid = f"rbi-pair-{doc_id}-{pos}"
                en[pos]["pair_id"] = pid
                hi[pos]["pair_id"] = pid
                info["paired"] += 1
        if fails:
            info["note"] = f"{fails} row(s) failed the number check and were left unpaired"
        elif en[min(en)]["doc_date"] != hi[min(hi)]["doc_date"]:
            info["note"] = "paired, but EN/HI page dates differ"
    return report


# ---------------------------------------------------------------- outputs

def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0
    k = (len(sorted_vals) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo))


def norm_q(q):
    return re.sub(r"[^\w\u0900-\u097F]+|_", " ", q.lower()).strip()


def pick_samples(rows, n=3):
    cand = [r for r in rows if 150 <= r["answer_chars"] <= 700] or rows
    if len(cand) <= n:
        return cand
    return [cand[int(len(cand) * f)] for f in (1 / 6, 1 / 2, 5 / 6)][:n]


def write_stats(path, rows, doc_report, pair_report, listings):
    by_lang = {l: [r for r in rows if r["lang"] == l] for l in LANGS}
    pairs = {r["pair_id"] for r in rows if r["pair_id"]}
    L = ["# RBI FAQ Q&A set: stats", "",
         f"Generated by `scripts/fetch_rbi.py`. Source: rbi.org.in/commonman, pages cached {max(r['retrieved_at'] for r in rows)}.", "",
         "## Totals", "", "| | English | Hindi |", "|---|---|---|",
         f"| Q&A rows | {len(by_lang['en'])} | {len(by_lang['hi'])} |",
         f"| Documents with rows | {len({r['doc_id'] for r in by_lang['en']})} | {len({r['doc_id'] for r in by_lang['hi']})} |",
         "", f"EN/HI pairs (rows carrying the same `pair_id`): **{len(pairs)}**", "",
         "## Rows per section and language", "",
         "| Section (SID) | EN rows | HI rows | EN docs | HI docs |", "|---|---|---|---|---|"]
    for sid, name in SECTIONS.items():
        e = [r for r in by_lang["en"] if r["section"] == name]
        h = [r for r in by_lang["hi"] if r["section"] == name]
        L.append(f"| {name} ({sid}) | {len(e)} | {len(h)} | {len({r['doc_id'] for r in e})} | {len({r['doc_id'] for r in h})} |")
    L += ["", "A document listed under several sections is counted once, under the first of these in the table order. "
          "SID 8 is titled 'Commercial Banking' on the site; it is labelled 'Banking' here.", "",
          "## Answer length (characters)", "",
          "| | n | min | p10 | p25 | median | p75 | p90 | max | mean |", "|---|---|---|---|---|---|---|---|---|---|"]
    for lang in LANGS:
        v = sorted(r["answer_chars"] for r in by_lang[lang])
        L.append(f"| {lang} | {len(v)} | {v[0]} | {pct(v, 10)} | {pct(v, 25)} | {pct(v, 50)} | {pct(v, 75)} | {pct(v, 90)} | {v[-1]} | {round(sum(v) / len(v))} |")
    L += ["", "Buckets (answer_chars):", "", "| | <100 | 100-299 | 300-999 | 1000-2999 | >=3000 |", "|---|---|---|---|---|---|"]
    for lang in LANGS:
        v = [r["answer_chars"] for r in by_lang[lang]]
        b = [sum(1 for x in v if x < 100), sum(1 for x in v if 100 <= x < 300), sum(1 for x in v if 300 <= x < 1000),
             sum(1 for x in v if 1000 <= x < 3000), sum(1 for x in v if x >= 3000)]
        L.append(f"| {lang} | " + " | ".join(map(str, b)) + " |")
    L += ["", "## Per-document report", "",
          "| Doc | Title (EN listing) | EN rows | HI rows | Paired | Note |", "|---|---|---|---|---|---|"]
    rep = defaultdict(dict)
    for d in doc_report:
        rep[d["doc_id"]][d["lang"]] = d
    for doc_id in sorted(rep):
        d = rep[doc_id]
        title = (d.get("en") or d.get("hi"))["listing_title"].replace("|", "/")
        notes = []
        for lang in LANGS:
            if lang in d and d[lang]["status"] != "ok":
                notes.append(f"{lang}: {d[lang]['status']}")
            if lang in d and d[lang].get("title_note"):
                notes.append(f"{lang}: {d[lang]['title_note']}")
            if lang in d and d[lang].get("rejected_question_like"):
                notes.append(f"{lang}: question-like lines not split: {d[lang]['rejected_question_like'][:2]}")
        if "en" not in d:
            notes.append("not in English listings")
        if "hi" not in d:
            notes.append("not in Hindi listings")
        pr = pair_report.get(doc_id, {})
        if pr.get("note"):
            notes.append(pr["note"])
        L.append(f"| {doc_id} | {title[:70]} | {pr.get('en', 0)} | {pr.get('hi', 0)} | {pr.get('paired', 0)} | {'; '.join(notes)} |")
    # data-quality checks
    L += ["", "## Data-quality checks", ""]
    for lang in LANGS:
        tr = [(d["doc_id"], t) for d in doc_report if d["lang"] == lang and d["status"] == "ok" for t in d.get("trimmed", [])]
        L.append(f"- Lines dropped from answer tails ({lang}): {len(tr)} (section headings between FAQs, and the RBI disclaimer footer on the last answer). "
                 + "First few: " + "; ".join(f"{d}: {t[:50]!r}" for d, t in tr[:4]) + ".")
    multi = sorted({(r["doc_id"], r["doc_title"], tuple(r["also_in_sections"])) for r in rows if r.get("also_in_sections")})
    L.append(f"- Documents listed under more than one of the chosen sections: {len(multi)}"
             + ("" if not multi else " (" + "; ".join(f"{d} -> also {', '.join(a)}" for d, _, a in multi) + ")") + ".")
    for lang in LANGS:
        groups = defaultdict(set)
        for r in by_lang[lang]:
            groups[norm_q(r["question"])].add(r["doc_id"])
        dup = {k: v for k, v in groups.items() if len(v) > 1}
        L.append(f"- Exact duplicate questions across different documents ({lang}): {len(dup)}"
                 + ("" if not dup else "; e.g. " + "; ".join(f'"{k[:60]}" in docs {sorted(v)}' for k, v in list(dup.items())[:3])) + ".")
    low = [r for r in by_lang["hi"] if deva_ratio(r["question"] + r["answer"]) < 0.3]
    L.append(f"- Hindi rows with under 30% Devanagari letters (mostly English terms or URLs): {len(low)}"
             + ("" if not low else " (ids: " + ", ".join(r["id"] for r in low[:10]) + ("..." if len(low) > 10 else "") + ")") + ".")
    short = [r["id"] for r in rows if r["answer_chars"] < 15]
    L.append(f"- Rows with answers under 15 characters: {len(short)}" + ("" if not short else f" ({', '.join(short[:10])})") + ".")
    only_en = sorted(set(listings["en"]) - set(listings["hi"]))
    only_hi = sorted(set(listings["hi"]) - set(listings["en"]))
    L.append(f"- Doc ids listed only in English: {only_en}; only in Hindi: {only_hi}.")
    L += ["", "## Sample rows (verbatim JSONL)", ""]
    for lang in LANGS:
        L += [f"### {lang}", "", "```json"]
        L += [json.dumps(r, ensure_ascii=False) for r in pick_samples(by_lang[lang])]
        L += ["```", ""]
    Path(path).write_text("\n".join(L), encoding="utf-8")


TERMS_PAGES = {
    "en_disclaimer.html": "https://www.rbi.org.in/commonman/English/Scripts/Disclaimer.aspx",
    "main_disclaimer.html": "https://www.rbi.org.in/Scripts/Disclaimer.aspx",
    "main_communication_policy.html": "https://www.rbi.org.in/Scripts/CommunicationPolicy.aspx",
}
TERMS_QUOTES = [
    ("main_disclaimer.html", "Every effort has been made to ensure the figures are correct. In case of doubt, however please check the print versions."),
    ("main_disclaimer.html", "The contents of this Web Site are provided on an \"as is\" basis without warranties of any kind."),
    ("main_disclaimer.html", "The contents on this Web Site do not constitute financial or other professional advice."),
    ("main_disclaimer.html", "Except as set forth below, caching and links to, and the framing of this Web Site or any of the contents are prohibited."),
    ("main_disclaimer.html", "\u00a9 Reserve Bank of India. All Rights Reserved."),
    ("en_disclaimer.html", "\u00a9 Reserve Bank of India. All Rights Reserved."),
]


def page_text(name):
    soup = BeautifulSoup(fetch(TERMS_PAGES[name], name), "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).replace("\xa0", " ")


def write_terms(path):
    texts = {n: page_text(n) for n in TERMS_PAGES}
    quotes = []
    for name, q in TERMS_QUOTES:
        if q not in texts[name]:
            raise RuntimeError(f"quoted sentence not found on {TERMS_PAGES[name]}: {q!r}")
        quotes.append((TERMS_PAGES[name], q))
    kw = re.compile(r"copyright|reproduc|republish|redistribut|licen[cs]|re-?use|permission|attribution", re.I)
    kw_hits = {}
    for n, t in texts.items():
        kw_hits[TERMS_PAGES[n]] = sorted({m.group(0).lower() for m in kw.finditer(t)})
    L = ["# RBI website terms: can we republish extracted FAQs?", "",
         "**Verdict: unclear, leaning no without permission.** The site has no licence for reuse or republication, "
         "no open-data statement, and no explicit ban on copying the FAQ text either. What it does say is "
         "all-rights-reserved plus a ban on 'caching' the site's contents. Do not assume republishing on Hugging Face is allowed.", "",
         "Not legal advice. Pages read on " + dt.date.today().isoformat() + ".", "",
         "## Exact sentences", ""]
    for url, q in quotes:
        L += [f"- {url}", f"  > {q}"]
    L += ["", "## What each says", "",
          "- Footer on every page, including the FAQ pages: all rights reserved. No Creative Commons or other licence is named anywhere I found.",
          "- The 'caching ... prohibited' sentence sits in the section on links to the site from other sites. "
          "It is about linking and framing, but its wording ('caching', 'any of the contents') could be read to cover keeping copies of content. Unclear.",
          "- The disclaimer says the content is provided as is, may be inaccurate, and is not professional advice. "
          "Any dataset card should say the answers are RBI text as of the retrieval date, not advice.",
          "- Nothing in the disclaimer or the Communication Policy page grants or refuses permission to reproduce text. "
          "A keyword scan of the three pages for copyright / reproduce / republish / redistribute / licence / reuse / permission / attribution found only:", ""]
    for url, hits in kw_hits.items():
        L.append(f"  - {url}: {', '.join(hits) if hits else 'nothing'}")
    L += ["", "The 'permission' hit is the sentence about hyper-linking and framing, not about reuse.", "",
          "## Other observations", "",
          "- `https://www.rbi.org.in/robots.txt` returned HTTP 418 ('Unauthorised Access') to a browser-UA request on 2026-11-12, "
          "so crawl rules could not be read. The FAQ pages themselves returned 200. Not worked around.",
          "- The Hindi disclaimer page (commonman/Hindi) is mostly in a legacy font and unreadable, so only the English text was used.", "",
          "## Options if you want to publish", "",
          "1. Ask RBI in writing for permission (contact address on the main site: helpdoc[at]rbi[dot]org[dot]in).",
          "2. Publish the script and a pointer to the source URLs, not the text. Anyone can rebuild the set with `python3 scripts/fetch_rbi.py`.",
          "3. If you publish text anyway, keep it to a small excerpt with the source URL, retrieval date, and 'Source: Reserve Bank of India' on every row, "
          "and state the licence status as unresolved in the dataset card.", ""]
    Path(path).write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        listings = collect_listings()
        rows, doc_report = build_rows(listings)
        pair_report = pair_rows(rows)
        write_terms(OUT / "TERMS.md")
    except Blocked as e:
        sys.exit(f"STOP: {e}")
    rows.sort(key=lambda r: (r["lang"], r["doc_id"], int(r["id"].rsplit("-", 1)[1])))
    en = [r for r in rows if r["lang"] == "en"]
    hi = [r for r in rows if r["lang"] == "hi"]
    write_jsonl(OUT / "rbi_faq_en.jsonl", en)
    write_jsonl(OUT / "rbi_faq_hi.jsonl", hi)
    write_stats(OUT / "STATS.md", rows, doc_report, pair_report, listings)
    pairs = len({r["pair_id"] for r in rows if r["pair_id"]})
    print(f"en rows: {len(en)}  hi rows: {len(hi)}  pairs: {pairs}  network requests: {_net_requests}")


if __name__ == "__main__":
    main()
