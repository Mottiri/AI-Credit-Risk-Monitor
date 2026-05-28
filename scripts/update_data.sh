#!/usr/bin/env sh
set -eu

python3 scripts/fetch_fred.py
python3 scripts/fetch_polymarket.py

printf '%s\n' 'Updated data/latest.json and data/polymarket.json.'
