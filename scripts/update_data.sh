#!/usr/bin/env sh
set -eu

python3 scripts/fetch_fred.py
python3 scripts/fetch_polymarket.py
python3 scripts/fetch_nvidia.py
python3 scripts/fetch_big_tech_capex.py
python3 scripts/fetch_broadcom.py
python3 scripts/fetch_hype.py
python3 scripts/merge_external_data.py

printf '%s\n' 'Updated data/latest.json, data/polymarket.json, data/nvidia.json, data/big-tech-capex.json, data/broadcom.json, and data/hype.json.'
