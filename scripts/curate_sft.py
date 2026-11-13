"""Clean the assembled fine-tuning rows with CuratorKIT before training.

MinHash near-duplicate removal, text cleaning, secrets gate, PII pseudonymization (helpline phone numbers are kept on
purpose: they are public RBI/bank numbers the assistant must be able to quote), multilingual toxicity gate.
Usage: python curate_sft.py sft_raw.jsonl OUT_DIR
"""
import sys, json
from curatorkit import Curator, CuratorConfig
cfg = CuratorConfig(dataset=sys.argv[1], format="auto", dedup="minhash", minhash_threshold=0.85, clean=True, min_tokens=3,
                    secrets_gate=True, pii_pseudonymize=True,
                    pii_entity_types=["EMAIL_ADDRESS", "CREDIT_CARD", "IBAN_CODE", "US_SSN", "IP_ADDRESS"],
                    toxicity_gate=True, toxicity_detoxify_model="multilingual",
                    export_formats=["sharegpt"], output_dir=sys.argv[2])
res = Curator(cfg).run()
res.print_summary()
