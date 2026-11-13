#!/usr/bin/env bash
# Bootstrap inside nvidia/cuda:13.0.3-devel-ubuntu24.04 (vLLM 0.33 JIT-compiles kernels and needs nvcc, which the
# plain uv image lacks): install uv, then run a jobs/*.py uv script from GitHub at the pinned commit.
# usage: bash cuda_boot.sh SHA SCRIPT [args...]
set -euo pipefail
SHA=$1; SCRIPT=$2; shift 2
apt-get update -qq && apt-get install -y -qq curl ca-certificates git >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null && . "$HOME/.local/bin/env"
curl -sL "https://raw.githubusercontent.com/tayyab415/rounded-off/$SHA/jobs/$SCRIPT" -o "/tmp/$SCRIPT"
export CUDA_HOME=/usr/local/cuda
exec uv run --python 3.12 "/tmp/$SCRIPT" --sha "$SHA" "$@"
