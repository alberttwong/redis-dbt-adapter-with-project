#!/usr/bin/env bash
# Download the NYC TLC yellow taxi trips CSV (January 2019, ~7.7M rows, 134 MB
# gzipped) from the DataTalksClub mirror. The TLC itself now publishes Parquet
# only.
set -euo pipefail

BASE="https://github.com/DataTalksClub/nyc-tlc-data/releases/download"
MONTH="${MONTH:-2019-01}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${ROOT}/data"

FILE="yellow_tripdata_${MONTH}.csv.gz"
if [ -f "${ROOT}/data/${FILE}" ]; then
  echo "data/${FILE} already exists"
else
  curl -fSL --progress-bar -o "${ROOT}/data/${FILE}" "${BASE}/yellow/${FILE}"
fi

# Zone lookup ships as a dbt seed (seeds/taxi_zone_lookup.csv); refresh it with:
#   curl -fsSL -o seeds/taxi_zone_lookup.csv "${BASE}/misc/taxi_zone_lookup.csv"
