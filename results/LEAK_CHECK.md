# Train/test leak check (RULE LEAK-1)

Script: `scripts/leak_check.py` (run: `python3 -I scripts/leak_check.py`). CPU only, no network.
Normalisation: Unicode NFKC, lowercase, punctuation to space, whitespace collapsed. Exact = equal normalised strings. Near = character 5-gram Jaccard >= 0.8 (exact matches are included in the near count). Share = near / eval set size. Rows over 1% are marked **yes**.

SFT source: `data/sft_raw.jsonl`, 2,992 user turns. The 2,985-row CuratorKIT output (`sft_sharegpt.jsonl`) is not in this checkout, so section (a) checks the 2,992-row file it was cut from. Every kept row is in it, so (a) counts are an upper bound (at most 7 extra rows).

BankDesk: each card has three openings (ambiguous, clear scam, clear genuine). A test card counts as matched if any of its openings matches any opening of a training card.

## What it shows

46 rows checked; 44 have no near match. Over 1% near matches: SFT user turns vs bank_task hi, 5 of 155 (3.2%), 3 exact. Harmful sets, refusal prompts and BankDesk cards have no near match: the highest Jaccard is 0.45 between SFT turns and any harmful set, and 0.68 in sections (b) and (c). Every match found is a short Banking77 query; a near match on a short query is not always the same question (see the examples).

## (a) SFT user turns against chat eval sets

| train source | eval set | lang | eval n | exact | near (J>=0.8) | near % | max J | >1% |
|---|---|---|---:|---:|---:|---:|---:|---|
| SFT user turns (2992) | bank_task | en | 308 | 0 | 2 | 0.7 | 0.93 | no |
| SFT user turns (2992) | bank_task | hi | 155 | 3 | 5 | 3.2 | 1.00 | **yes** |
| SFT user turns (2992) | bank_redteam | en | 250 | 0 | 0 | 0.0 | 0.17 | no |
| SFT user turns (2992) | bank_redteam | hi | 250 | 0 | 0 | 0.0 | 0.16 | no |
| SFT user turns (2992) | bank_borderline | en | 400 | 0 | 0 | 0.0 | 0.21 | no |
| SFT user turns (2992) | bank_borderline | hi | 395 | 0 | 0 | 0.0 | 0.27 | no |
| SFT user turns (2992) | scam_victim | en | 300 | 0 | 0 | 0.0 | 0.16 | no |
| SFT user turns (2992) | scam_victim | hi | 300 | 0 | 0 | 0.0 | 0.16 | no |
| SFT user turns (2992) | genuine_urgent | en | 250 | 0 | 0 | 0.0 | 0.25 | no |
| SFT user turns (2992) | genuine_urgent | hi | 250 | 0 | 0 | 0.0 | 0.27 | no |
| SFT user turns (2992) | rbi_qa | en | 150 | 0 | 0 | 0.0 | 0.32 | no |
| SFT user turns (2992) | rbi_qa | hi | 150 | 0 | 0 | 0.0 | 0.29 | no |
| SFT user turns (2992) | xstest_safe | en | 250 | 0 | 0 | 0.0 | 0.40 | no |
| SFT user turns (2992) | xstest_safe | hi | 248 | 0 | 0 | 0.0 | 0.49 | no |
| SFT user turns (2992) | xstest_unsafe | en | 200 | 0 | 0 | 0.0 | 0.38 | no |
| SFT user turns (2992) | xstest_unsafe | hi | 200 | 0 | 0 | 0.0 | 0.45 | no |
| SFT user turns (2992) | harmbench | en | 150 | 0 | 0 | 0.0 | 0.15 | no |
| SFT user turns (2992) | harmbench | hi | 148 | 0 | 0 | 0.0 | 0.19 | no |

## (b) SafeGrad refusal prompts against HarmBench and XSTest-unsafe (ids only)

| train source | eval set | lang | eval n | exact | near (J>=0.8) | near % | max J | >1% |
|---|---|---|---:|---:|---:|---:|---:|---|
| SafeGrad refusals_train (823) | harmbench | en | 150 | 0 | 0 | 0.0 | 0.51 | no |
| SafeGrad refusals_train (823) | harmbench | hi | 148 | 0 | 0 | 0.0 | 0.55 | no |
| SafeGrad refusals_train (823) | xstest_unsafe | en | 200 | 0 | 0 | 0.0 | 0.40 | no |
| SafeGrad refusals_train (823) | xstest_unsafe | hi | 200 | 0 | 0 | 0.0 | 0.37 | no |
| AdvBench parquet (424) (424) | harmbench | en | 150 | 0 | 0 | 0.0 | 0.51 | no |
| AdvBench parquet (424) (424) | harmbench | hi | 148 | 0 | 0 | 0.0 | 0.09 | no |
| AdvBench parquet (424) (424) | xstest_unsafe | en | 200 | 0 | 0 | 0.0 | 0.40 | no |
| AdvBench parquet (424) (424) | xstest_unsafe | hi | 200 | 0 | 0 | 0.0 | 0.03 | no |

## (c) BankDesk card openings against test cards

| train source | eval set | lang | eval n | exact | near (J>=0.8) | near % | max J | >1% |
|---|---|---|---:|---:|---:|---:|---:|---|
| cards v3 train (411) | v3 test (111) | en | 67 | 0 | 0 | 0.0 | 0.48 | no |
| cards v3 train (411) | v3 test (111) | hi | 44 | 0 | 0 | 0.0 | 0.53 | no |
| cards v3 train (411) | test2 (273) | en | 96 | 0 | 0 | 0.0 | 0.46 | no |
| cards v3 train (411) | test2 (273) | hi | 177 | 0 | 0 | 0.0 | 0.42 | no |
| cards v3 dev (85) | v3 test (111) | en | 67 | 0 | 0 | 0.0 | 0.46 | no |
| cards v3 dev (85) | v3 test (111) | hi | 44 | 0 | 0 | 0.0 | 0.54 | no |
| cards v3 dev (85) | test2 (273) | en | 96 | 0 | 0 | 0.0 | 0.42 | no |
| cards v3 dev (85) | test2 (273) | hi | 177 | 0 | 0 | 0.0 | 0.68 | no |
| cards dev2 (65) | v3 test (111) | en | 67 | 0 | 0 | 0.0 | 0.41 | no |
| cards dev2 (65) | v3 test (111) | hi | 44 | 0 | 0 | 0.0 | 0.47 | no |
| cards dev2 (65) | test2 (273) | en | 96 | 0 | 0 | 0.0 | 0.41 | no |
| cards dev2 (65) | test2 (273) | hi | 177 | 0 | 0 | 0.0 | 0.51 | no |
| cards rl_all (438) | v3 test (111) | en | 67 | 0 | 0 | 0.0 | 0.63 | no |
| cards rl_all (438) | v3 test (111) | hi | 44 | 0 | 0 | 0.0 | 0.40 | no |
| cards rl_all (438) | test2 (273) | en | 96 | 0 | 0 | 0.0 | 0.49 | no |
| cards rl_all (438) | test2 (273) | hi | 177 | 0 | 0 | 0.0 | 0.66 | no |
| cards all train+dev+dev2+rl (999) | v3 test (111) | en | 67 | 0 | 0 | 0.0 | 0.63 | no |
| cards all train+dev+dev2+rl (999) | v3 test (111) | hi | 44 | 0 | 0 | 0.0 | 0.54 | no |
| cards all train+dev+dev2+rl (999) | test2 (273) | en | 96 | 0 | 0 | 0.0 | 0.49 | no |
| cards all train+dev+dev2+rl (999) | test2 (273) | hi | 177 | 0 | 0 | 0.0 | 0.68 | no |

## Within-set duplicates: bank task (Banking77 test queries)

| lang | n | exact pairs | near pairs | items in an exact pair | items in a near pair |
|---|---:|---:|---:|---:|---:|
| en | 308 | 0 | 1 | 0 | 2 |
| hi | 155 | 0 | 0 | 0 | 0 |

## Near-match ids

Harmful and RBI sets: eval id -> best training id, Jaccard. No text.

- None: no harmful or RBI eval prompt has a near match.

## Examples (benign sets only, up to 3 per row, 100 characters each)

**SFT user turns vs bank_task en**
- J=0.93 eval `b77t-268`: "I don't live in the UK.  Can I still get a card?" / train `sft_raw#2555`: "If I don't live in the UK, can I still get a card?"
- J=0.81 eval `b77t-434`: 'What do i have to do to change my name?' / train `sft_raw#204`: 'What do I have to do to change my pin?'

**SFT user turns vs bank_task hi**
- J=1.00 eval `b77t-189`: 'मेरा कार्ड अभी तक नहीं आया है।' / train `sft_raw#2689`: 'मेरा कार्ड अभी तक नहीं आया है।'
- J=1.00 eval `b77t-289`: 'मुझे अपना कार्ड जल्द से जल्द चाहिए।' / train `sft_raw#783`: 'मुझे अपना कार्ड जल्द से जल्द चाहिए।'
- J=1.00 eval `b77t-457`: 'खाता खोलने के लिए न्यूनतम आयु क्या है?' / train `sft_raw#1714`: 'खाता खोलने के लिए न्यूनतम आयु क्या है?'

**bank task en, within-set pairs**
- J=0.85 `b77t-71`: 'I would like to transfer some money from my other bank account into this one.' / `b77t-197`: 'I would like to transfer money from my other bank account into this one.'

