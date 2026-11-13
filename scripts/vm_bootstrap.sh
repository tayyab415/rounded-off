#!/usr/bin/env bash
# One-time VM setup: swap, uv, two Python 3.12 envs, Lexsi libraries, model downloads.
set -euo pipefail
mkdir -p ~/logs ~/work ~/hfcache
export HF_HOME=~/hfcache
if ! swapon --show | grep -q swapfile; then sudo fallocate -l 24G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile; fi
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH=$HOME/.local/bin:$PATH
cd ~/work
for r in SafeTune CircuitKIT AuditKIT CuratorKIT; do [ -d $r ] || git clone -q https://github.com/Lexsi-Labs/$r.git; done
for r in SafeTune CircuitKIT AuditKIT CuratorKIT; do echo "$r $(git -C $r rev-parse --short HEAD)"; done > ~/work/lexsi_commits.txt

# Env A: Lexsi stack + llm-compressor (no vLLM)
uv venv -q -p 3.12 ~/envA
. ~/envA/bin/activate
uv pip install -q "torch==2.14.*" --index-url https://download.pytorch.org/whl/cu130 || uv pip install -q "torch==2.14.*"
uv pip install -q -e ./SafeTune -e ./CircuitKIT -e "./AuditKIT[transformers,interop]" -e "./CuratorKIT[all]"
uv pip install -q -e "./CircuitKIT[quantization]" "llmcompressor>=0.15" "transformers>=5.16.1,<5.21" hf_transfer
python -c "import torch,transformers;print('envA torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__)"
python -c "import circuitkit, safetune, auditkit, curatorkit; print('envA libs import ok')"
deactivate

# Env B: vLLM for generation and judging
uv venv -q -p 3.12 ~/envB
. ~/envB/bin/activate
uv pip install -q "vllm>=0.33" "transformers>=5.16.1,<5.21" hf_transfer pandas pyarrow
python -c "import vllm,transformers,torch;print('envB vllm',vllm.__version__,'tf',transformers.__version__,'torch',torch.__version__)"

# Models
export HF_HUB_ENABLE_HF_TRANSFER=1
hf download CohereLabs/tiny-aya-global --quiet >/dev/null && echo "got tiny-aya-global"
hf download Qwen/Qwen3Guard-Gen-8B --quiet >/dev/null && echo "got Qwen3Guard-Gen-8B"
hf download CohereLabs/tiny-aya-base --quiet >/dev/null && echo "got tiny-aya-base" || echo "tiny-aya-base not accessible yet"
echo BOOTSTRAP_DONE
