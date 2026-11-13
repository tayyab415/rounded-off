# CuratorKIT gates vs planted harmful rows (2026-11-13)

Input: 2,985 cleaned bank rows + 332 BeaverTails unsafe rows (10%), `scripts/build_contaminated.py`, seed 13.
CuratorKIT config: `scripts/curate_sft.py` (MinHash dedup, cleaning, secrets, PII, Detoxify-multilingual toxicity gate).

- Rejected 131 rows, all by `toxic_content`. All 131 were planted harmful rows: 131/332 caught (39.5%), 0/2,985 clean rows rejected.
- By BeaverTails top category (caught / planted):

| category | caught |
|---|---|
| sexually_explicit,adult_content | 19/22 (86.4%) |
| hate_speech,offensive_language | 16/25 (64.0%) |
| discrimination,stereotype,injustice | 15/24 (62.5%) |
| self_harm | 13/21 (61.9%) |
| animal_abuse | 11/22 (50.0%) |
| controversial_topics,politics | 11/23 (47.8%) |
| violence,aiding_and_abetting,incitement | 13/28 (46.4%) |
| non_violent_unethical_behavior | 12/27 (44.4%) |
| misinformation_regarding_ethics,laws_and_safety | 8/24 (33.3%) |
| child_abuse | 7/22 (31.8%) |
| terrorism,organized_crime | 3/22 (13.6%) |
| privacy_violation | 2/25 (8.0%) |
| drug_abuse,weapons,banned_substance | 1/24 (4.2%) |
| financial_crime,property_crime,theft | 0/23 (0.0%) |

Reading: a toxicity gate measures offensive language, not harmful instructions. For a bank, the category that matters most
(financial crime) passes untouched. Feature request for CuratorKIT: an optional harm-classifier gate (e.g. a guard model).
