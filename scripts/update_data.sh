#!/usr/bin/env sh
set -eu

python3 scripts/fetch_fred.py
python3 scripts/fetch_polymarket.py
python3 scripts/merge_external_data.py

printf '%s\n' 'Updated data/latest.json and data/polymarket.json.'
