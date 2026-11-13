"""Download a processed Adaption dataset as JSONL using the Adaption Python SDK.

Reads ADAPTION_API_KEY from ~/.config/adaption/env. Usage: python adaption_download.py DATASET_ID OUT.jsonl
"""
import os, sys
from adaption import Adaption
key = os.environ.get("ADAPTION_API_KEY", "")
if not key:
    for l in open(os.path.expanduser("~/.config/adaption/env")):
        l = l.strip().removeprefix("export ").strip()
        if l.startswith("ADAPTION_API_KEY="): key = l.split("=", 1)[1].strip().strip("'\"")
c = Adaption(api_key=key)
r = c.datasets.download(sys.argv[1], file_format="jsonl")
r.write_to_file(sys.argv[2])
print("saved", sys.argv[2], os.path.getsize(sys.argv[2]), "bytes")
