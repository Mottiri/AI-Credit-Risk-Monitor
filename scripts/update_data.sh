#!/usr/bin/env sh
set -eu

python3 scripts/fetch_fred.py

printf '%s\n' 'Updated data/latest.json from FRED.'
