#!/usr/bin/env bash
# Classifica as teses da BDTD por ODS com o modelo Aurora SDG mBERT (mesmo do OpenAlex),
# num container linux/amd64 isolado. Requer: models/aurora_sdg_mbert.h5 (baixado do Zenodo)
# e data/bdtd_uftm.csv. Gera data/bdtd_sdg.csv.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f models/aurora_sdg_mbert.h5 ]; then
  echo "Falta models/aurora_sdg_mbert.h5 — baixe do Zenodo 7304547." >&2
  exit 1
fi

echo "==> Construindo imagem (uma vez)..."
docker build --platform=linux/amd64 -f Dockerfile.sdg -t bdtd-sdg .

echo "==> Classificando..."
docker run --rm --platform=linux/amd64 \
  -v "$PWD/data:/app/data" \
  -v "$PWD/models:/app/models:ro" \
  -v "$PWD/fetch_bdtd_sdg.py:/app/fetch_bdtd_sdg.py:ro" \
  bdtd-sdg

echo "==> Pronto: data/bdtd_sdg.csv"
