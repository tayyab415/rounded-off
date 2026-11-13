# API prices used for the ROI table (fetched 2026-11-13 from the official pages)

Source OpenAI: https://developers.openai.com/api/docs/pricing.md (copy: openai_pricing_2026-11-13.md), "Standard pricing", short context, USD per 1M tokens.
Source Google: https://ai.google.dev/gemini-api/docs/pricing, Gemini 3.5 Flash-Lite, paid tier, standard.

| model | input $/1M | output $/1M |
|---|---|---|
| gpt-6-luna | 0.10 | 0.50 |
| gpt-6.1-terra | 1.00 | 5.00 |
| gpt-5.4-mini | 0.75 | 4.50 |
| gemini-3.5-flash-lite | 0.30 | 2.50 |

Self-hosting: AWS g6.xlarge (1x NVIDIA L4) on-demand us-east-1 $0.8048/h (our launch, 2026-11-12). Throughput measured from our vLLM runs.
