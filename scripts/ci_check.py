#!/usr/bin/env python3
"""Checks for CI (.github/workflows/ci.yml).

    scripts/ci_check.py results --pass 77 --warn 1
        dbt's last run (target/run_results.json) had exactly these results,
        and no errors, failures or skips.

    scripts/ci_check.py demo incremental-demo
        Runs the Makefile demo with JSON logs, prints its log as usual, and
        checks the numbers its `dbt show` commands print.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# dbt's summary line counts both "success" (models, seeds, snapshots) and
# "pass" (tests) as PASS.
STATUS_NAMES = {"success": "PASS", "pass": "PASS", "warn": "WARN", "error": "ERROR", "fail": "ERROR", "skipped": "SKIP"}


def check_results(expected_pass: int, expected_warn: int) -> int:
    path = ROOT / os.environ.get("DBT_TARGET_PATH", "target") / "run_results.json"
    results = json.loads(path.read_text())["results"]
    counts = Counter(STATUS_NAMES.get(r["status"], r["status"].upper()) for r in results)
    print(" ".join(f"{name}={counts[name]}" for name in ["PASS", "WARN", "ERROR", "SKIP"]), f"TOTAL={len(results)}")

    others = {name: n for name, n in counts.items() if name not in ("PASS", "WARN")}
    if counts["PASS"] == expected_pass and counts["WARN"] == expected_warn and not others:
        return 0
    print(f"Expected PASS={expected_pass} WARN={expected_warn} and nothing else", file=sys.stderr)
    for r in results:
        if STATUS_NAMES.get(r["status"]) != "PASS":
            print(f"  {r['status']}: {r['unique_id']}: {(r.get('message') or '').strip()}", file=sys.stderr)
    return 1


# --- demos -------------------------------------------------------------------


def check_incremental(shows):
    # The first half of January, then all of it. agg_zone_daily's zone-day
    # totals always add up to fct_trips.
    return expect_rows(
        shows,
        [
            [{"trips": 71293, "last_pickup": "2019-01-15T23:59:51", "zone_day_trips": 71293, "zone_days": 1784}],
            [{"trips": 152686, "last_pickup": "2019-01-31T23:58:43", "zone_day_trips": 152686, "zone_days": 3698}],
        ],
    )


def check_snapshot(shows):
    # Zone 132's history ends with the old name, closed when the rename was
    # recorded, and the new name, still current.
    if len(shows) != 1:
        return [f"expected 1 dbt show, got {len(shows)}"]
    rows = shows[0]
    if len(rows) < 2:
        return [f"expected at least 2 versions of zone 132, got {rows}"]
    old, new = rows[-2:]
    problems = []
    if old["Zone"] != "JFK Airport" or old["dbt_valid_to"] != new["dbt_valid_from"]:
        problems.append(f"expected 'JFK Airport', closed when the rename was recorded; got {old}")
    if new["Zone"] != "JFK International Airport" or new["dbt_valid_to"] is not None:
        problems.append(f"expected 'JFK International Airport', still current; got {new}")
    problems += [f"expected an earlier version to be closed; got {row}" for row in rows[:-1] if row["dbt_valid_to"] is None]
    return problems


def check_microbatch(shows):
    # Three daily batches; re-running January 2 leaves the same count.
    return expect_rows(
        shows,
        [
            [
                {"pickup_date": "2019-01-01", "trips": 3766},
                {"pickup_date": "2019-01-02", "trips": 3939},
                {"pickup_date": "2019-01-03", "trips": 4438},
            ]
        ],
    )


DEMOS = {"incremental-demo": check_incremental, "snapshot-demo": check_snapshot, "microbatch-demo": check_microbatch}


def expect_rows(shows, expected):
    if shows == expected:
        return []
    return [f"expected the dbt show commands to print\n  {expected}\ngot\n  {shows}"]


def run_demo(name: str) -> int:
    # DBT and SHOW_FLAGS are Makefile variables.
    cmd = ["make", name, "DBT=uv run dbt --log-format json", "SHOW_FLAGS=--output json"]
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    shows = []
    for line in proc.stdout:
        try:
            event = json.loads(line)
        except ValueError:
            print(line, end="", flush=True)  # make's own output
            continue
        print(event["info"]["msg"], flush=True)
        if event["info"]["name"] == "ShowNode":
            shows.append(json.loads(event["data"]["preview"]))
    if proc.wait() != 0:
        return proc.returncode

    problems = DEMOS[name](shows)
    for problem in problems:
        print(f"{name}: {problem}", file=sys.stderr)
    if not problems:
        print(f"{name}: the numbers are as expected")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    results = sub.add_parser("results", help="check target/run_results.json")
    results.add_argument("--pass", dest="passed", type=int, required=True)
    results.add_argument("--warn", type=int, default=0)
    demo = sub.add_parser("demo", help="run a Makefile demo and check its numbers")
    demo.add_argument("name", choices=sorted(DEMOS))
    args = parser.parse_args()

    if args.command == "results":
        return check_results(args.passed, args.warn)
    return run_demo(args.name)


if __name__ == "__main__":
    sys.exit(main())
