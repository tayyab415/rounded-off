"""ROI: cost per 1M bank answers, self-hosted Tiny Aya on one L4 vs closed APIs.

Self-hosted throughput comes from our own vLLM runs (answers/hour, median over bf16 models, greedy, 256 max new tokens).
API cost uses official list prices (notes/pricing/PRICES.md, fetched 2026-11-13) with the same output length and an
assumed 250 input tokens per chat (user message + a short bank system prompt; the API needs no 366-token Cohere preamble).
Usage: python3 -I scripts/roi.py ANSWERS_PER_HOUR MEAN_OUT_TOKENS [GPU_PRICE_PER_HOUR] [UTILIZATION]
"""
import sys
aph, out_tok = float(sys.argv[1]), float(sys.argv[2])
gpu = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8048
util = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
in_tok = 250
prices = {"gpt-6-luna": (0.10, 0.50), "gemini-3.5-flash-lite": (0.30, 2.50), "gpt-5.4-mini": (0.75, 4.50), "gpt-6.1-terra": (1.00, 5.00)}
self_cost = 1e6 / (aph * util) * gpu
print(f"| option | $ per 1M answers | x self-hosted |\n|---|---|---|")
print(f"| Tiny Aya on 1x L4 (AWS g6.xlarge ${gpu}/h, {int(util*100)}% busy) | {self_cost:,.0f} | 1.0 |")
for m, (pi, po) in prices.items():
    c = in_tok * pi + out_tok * po
    print(f"| {m} (${pi}/${po} per 1M in/out) | {c:,.0f} | {c/self_cost:.1f} |")
