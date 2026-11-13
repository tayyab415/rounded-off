"""Write a Hugging Face model card (README.md) into a checkpoint folder.
Usage: python model_card.py CKPT_DIR REPO_ID "one-line description" "how it was made" [--research-only]
"""
import sys, os
d, repo, desc, how = sys.argv[1:5]; research = "--research-only" in sys.argv
card = f"""---
license: cc-by-nc-4.0
base_model: CohereLabs/tiny-aya-global
language: [en, hi]
library_name: transformers
tags: [lexsi-hackathon, safety, banking, tiny-aya, safetune]
---
# {repo.split('/')[-1]}

{desc}

Part of **Rounded Off: do safety repairs survive 4-bit?** (Lexsi Labs AI Safety & Alignment Hackathon, Nov 2026).
Code and full results: https://github.com/tayyab415/rounded-off

**How it was made:** {how}

**Base model and license:** derived from [CohereLabs/tiny-aya-global](https://huggingface.co/CohereLabs/tiny-aya-global)
(CC-BY-NC-4.0); this checkpoint carries the same non-commercial license. Built with Lexsi Labs' SafeTune (Lexsi Source
Available License): {"this is a research artifact and must not be deployed in a production, user-facing or agentic system" if research else "evaluate safety yourself before any deployment"}.

**Intended use:** research on safety drift, repair and quantization. Not a production banking assistant.
"""
open(os.path.join(d, "README.md"), "w").write(card); print("card written", d)
