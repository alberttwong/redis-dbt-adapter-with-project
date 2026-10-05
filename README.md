# dbt Redis adapter with example NYC taxi trips DBT project

A dbt Core project that tests the dbt Redis adapter, which is built on the
[Redis ADBC driver](https://github.com/alberttwong/redis-adbc-driver). It does
three things:

- loads the NYC TLC yellow-taxi trips CSV into Redis,
- transforms it with ordinary dbt SQL: views, tables, an incremental MERGE
  fact table, a microbatch model, a snapshot, a model contract, joins, window
  functions, CTEs and `QUALIFY`,
- tests and documents it with dbt's standard commands, and stores the model
  descriptions in Redis as comments.

dbt's own default materializations do the work: tables, views, incremental
models (temporary tables plus `MERGE` or delete+insert) and snapshots. The SQL
dbt generates runs on the driver unchanged.

```
dbt  ──►  dbt-redis-adbc (adapter/)  ──►  adbc_driver_manager  ──►  libadbc_driver_redis  ──►  Redis 8
          Python + Jinja                  ADBC DB-API              SQL → FT.AGGREGATE / HASH
```

## Quick start

Requirements: Docker, [uv](https://docs.astral.sh/uv/) (it provides Python
3.10–3.13 for dbt), and network access to hub.getdbt.com for `dbt deps`. Building the driver from source also needs Go 1.26+ and a
C toolchain; on macOS arm64 and Linux (x86-64, arm64) the prebuilt one is used.

```bash
make setup
```

`make setup` does four things:

- runs `uv sync` and `dbt deps` (dbt_utils, and the local `redis_adbc_utils`)
- puts the driver in `driver/`: the prebuilt library from the pinned
  release (`v0.0.11`, in `scripts/driver-version`), after checking its SHA-256.
  Where the release has no build (another platform, or `DRIVER_VERSION` set
  to a commit) it builds the driver from source instead; `make driver-build`
  always does
- downloads the CSV into `data/`
- starts Redis **8.6.2**, the version Redis Cloud runs, on port 6380

```bash
make all
```

`make all` runs `dbt debug`, `seed`, `run-operation load_raw_trips`, `build`
and `docs generate`. Three demos show what happens across runs.

Load the first half of January, then the rest: `fct_trips` merges the new trips, and `agg_zone_daily` replaces the zone-days they touch (delete+insert on a composite key):

```bash
make incremental-demo
```

Rename a zone between two snapshots; its history keeps both versions:

```bash
make snapshot-demo
```

Backfill January 1–3 as three daily batches (run in parallel), then re-run
January 2 alone, which replaces only that day:

```bash
make microbatch-demo
```

Use `make docs-serve` to browse the docs and lineage graph.

Redis is published on **6380** so it doesn't collide with a local Redis on
6379. Override the connection with `REDIS_URI` (for example
`rediss://host:port/0` for Redis Cloud), credentials with `REDIS_USERNAME` and
`REDIS_PASSWORD`, and the driver location with `REDIS_ADBC_DRIVER`. A password
in `REDIS_URI` works too; `dbt debug` and the logs show it as `****`. Redis
Flex (RAM + SSD) databases aren't supported: their Search lacks features every
table needs, so the driver refuses them when it connects.

## dbt commands this project exercises

| Command | What happens in Redis |
|-|-|
| `dbt debug` | Opens an ADBC connection. The driver checks that the Query Engine is available (`FT._LIST`) and that `FT.AGGREGATE` works, which is how it refuses Redis Flex |
| `dbt seed` | 4 lookup CSVs (zones, payment types, rate codes, vendors), loaded with ADBC bulk ingest; reloads use `TRUNCATE` |
| `dbt run-operation load_raw_trips` | Streams the 134 MB gzipped CSV with pyarrow, keeps every 50th row (~153k trips across January), adds `trip_id` (the trip's row number in the file), and bulk-ingests it into `raw.yellow_tripdata` in 6–10 s |
| `dbt run` | 5 views and 8 tables, rebuilt with dbt's create-then-`ALTER … RENAME` swap; plus 2 incremental models built from a `CREATE TEMPORARY TABLE`: `fct_trips` with `MERGE`, and `agg_zone_daily` with delete+insert on `(pickup_date, pickup_location_id)`. `dim_zones` has an enforced contract, so it's created from its DDL (with `NOT NULL` and `CHECK` constraints) and then filled with `INSERT`. The marts' descriptions are stored with `COMMENT ON` |
| `dbt run --event-time-start … --event-time-end …` | `fct_trips_microbatch` (off unless `microbatch_demo` is set): one batch per pickup day; each batch deletes its day, then inserts it |
| `dbt snapshot` | `zones_snapshot`: SCD type 2 history of the zone lookup (check strategy; a deleted zone gets a closing version), written by dbt's snapshot `MERGE` |
| `dbt test` / `dbt build` | 56 data tests (`unique`, `not_null`, `accepted_values`, `relationships`, dbt_utils' `unique_combination_of_columns` / `accepted_range`, custom generic `non_negative` / `in_range`, 4 singular tests) and 2 unit tests |
| `dbt show`, `dbt compile`, `dbt ls` | Previews, inline queries, and the analysis in `analyses/` |
| `dbt build --empty --exclude-resource-type snapshot` | Builds and tests every model with no rows, in about 6 s. dbt reads each ref and source as `(select * from … where false limit 0)`, which the driver answers without reading the table. Tables, views and seeds are left empty (a view keeps the `where false limit 0` in its SQL; incremental models keep their rows), so run `make all` afterwards. Leave out the snapshot: with an empty source, `hard_deletes: new_record` would record every zone as deleted |
| `dbt docs generate` | Catalog built from ADBC `GetObjects` (column types, tables vs views), with the comments the marts store through `persist_docs` |

A clean `make all` takes 1.5–2 minutes on a laptop. It ends with 77 passes and 1
**intended** warning: the source test flags a $623,261.66 fare in the raw
data, which staging filters out.

## Project layout

```
models/
  staging/        views over raw + seeds: rename, type, filter, derive hour/weekday/duration
  intermediate/   int_trips_enriched: trips ⋈ zones (×2) ⋈ payment types ⋈ rate codes ⋈ vendors
  marts/          fct_trips (incremental MERGE), agg_zone_daily (incremental delete+insert on a
                  composite key), fct_trips_microbatch (optional), dim_zones
                  (enforced contract), agg_daily_revenue (7-day rolling average, LAG, RANK),
                  agg_top_pickup_zones (RANK … QUALIFY), agg_hourly_demand, agg_borough_flows,
                  agg_payment_mix, agg_airport_trips
snapshots/        zones_snapshot (SCD type 2 of the zone lookup)
seeds/            taxi_zone_lookup, payment_types, rate_codes, vendors
macros/           load_raw_trips and rename_zone (run-operations), day_part
tests/            generic (non_negative, in_range) and singular tests, including dbt's
                  cross-database macros
analyses/         top_pickup_zones_by_day_part
adapter/          the dbt-redis-adbc adapter package (installed editable by uv)
redis_adbc_utils/ redis_adbc__ overrides for dbt_utils, dbt_date and dbt_expectations macros
scripts/          download_driver.sh, build_driver.sh, driver-version, download_data.sh
```

Useful vars (defaults are in `dbt_project.yml`):

| Var | Default | Meaning |
|-|-|-|
| `raw_trips_sample_every` | `50` | Keep every Nth CSV row. `1` loads all ~7.7M rows, which needs several GB of Redis memory |
| `raw_trips_limit` | none | Cap on rows loaded |
| `trips_start` / `trips_end` | all of January 2019 | Pickup window kept by staging |
| `max_total_amount` | `2000` | Larger totals are treated as data errors |
| `lookback_hours` | `6` | Hours before the latest loaded pickup that each incremental run re-merges |
| `top_zones_per_borough` | `3` | Zones kept per borough by `agg_top_pickup_zones` |
| `microbatch_demo` | `false` | Enables `fct_trips_microbatch` |

## What the adapter does

dbt only connects to a database through an adapter package, and there is no
generic ADBC adapter. `adapter/` is a small one: about 570 lines of Python and
190 lines of macros. The driver runs the SQL of dbt's default macros and
materializations, so the adapter covers what isn't SQL:

| Area | Adapter |
|-|-|
| Connection | `adbc_driver_manager` DB-API, autocommit. The driver has no transactions: it accepts dbt's `BEGIN`/`COMMIT` as no-ops, and a `SET LOCAL` lasts until the model's `COMMIT`, as on Postgres. Results over 65,536 rows stream from the driver, so an error in a later batch is raised as dbt reads the rows; the adapter reports it as a database error, like one from the query. Ctrl-C and `--fail-fast` cancel the running statements (ADBC `StatementCancel`) |
| Metadata | Relations, columns and the docs catalog come from ADBC `GetObjects`; table comments come from `information_schema.tables`. Relations are matched with their case, since the driver keeps schema and table names as written (`alias='MyTable'` works). Column types are parsed as dbt-postgres reports them (`numeric` with precision and scale, `character varying` with its length) |
| `persist_docs` | Descriptions are stored with `COMMENT ON TABLE` / `VIEW` / `COLUMN`; the marts turn it on |
| `grants` | Skipped with a warning (see [Known limitations](#known-limitations)) |
| Temporary tables | `make_temp_relation` renders them unqualified (a schema-qualified name always means a permanent table), and their columns are looked up under `pg_temp` |
| Incremental strategies | `append`, `delete+insert` (the default with a `unique_key`), `merge`, and `microbatch` (each batch replaces its `event_time` window; batches can run in parallel) |
| Seed reloads | A reload without `--full-refresh` checks the CSV's columns before truncating, so a mismatch leaves the table as it was (there's no transaction to roll the `TRUNCATE` back) |
| Loading | Seeds and the raw CSV go through Arrow bulk ingest, which is much faster than INSERTs. The driver converts each seed value to its column's type as an INSERT would, and supplies the Arrow type for each of the raw CSV's SQL column types |
| Cross-database macros | dbt-core's defaults work natively except two: `safe_cast` uses the driver's `TRY_CAST`, and `listagg` with `limit_num` raises a clear error (it needs arrays). `tests/assert_cross_db_macros.sql` checks them all |
| Model contracts | An enforced contract creates the table from its DDL, then inserts the rows (as on dbt-postgres). `not_null` and `check` are enforced by the driver; `primary_key`, `unique` and `foreign_key` are accepted but not enforced (dbt warns) |
| Small dialect bits | `?` bind parameters, `CURRENT_TIMESTAMP`, a subquery wrapper for `dbt show --limit`, and no alias on the subqueries `--empty` and microbatch put around refs, so a model's own alias (`from {{ ref('x') }} z`) still works |

**Packages.** dbt looks for a package macro's adapter variants only in the
root project and the package itself, so the adapter can't fix a package's
`default__` macros that are wrong here. [`redis_adbc_utils/`](redis_adbc_utils/README.md)
holds those fixes:
- `dbt_utils.deduplicate`: the default drops rows with NULLs.
- dbt_expectations' regex `flags`: the default ignores them.
- dbt_date's day and month names, and its week and ISO-week macros: the
  defaults use Snowflake semantics.

This project installs it with dbt_utils and puts it first in
`dispatch:`. Copy that setup to use those packages with Redis.

Profile options (`profiles.yml`): `driver` (the library's path; without an
extension, the adapter adds `.dylib`, `.so` or `.dll`), `uri`, `username`,
`password`, `database` (optional; always `redis`), `schema`, `threads`,
`aggregate_pushdown` (`exact` / `all` / `none`), and `rename_rekey` (see
[Looking at the data in Redis](#looking-at-the-data-in-redis)).

## Driver issues found along the way

Building this project turned up these issues, all filed on
[alberttwong/redis-adbc-driver](https://github.com/alberttwong/redis-adbc-driver/issues).
All of them are fixed in the pinned driver, v0.0.11.

| Issue | Fixed in |
|-|-|
| [#13](https://github.com/alberttwong/redis-adbc-driver/issues/13) Bound string parameters read freed memory | [#15](https://github.com/alberttwong/redis-adbc-driver/pull/15) |
| [#17](https://github.com/alberttwong/redis-adbc-driver/issues/17), [#18](https://github.com/alberttwong/redis-adbc-driver/issues/18) Slow `IN (SELECT …)` (57 s → 0.9 s) and correlated `EXISTS` (28 s → 2 ms) | [#38](https://github.com/alberttwong/redis-adbc-driver/pull/38) |
| [#19](https://github.com/alberttwong/redis-adbc-driver/issues/19) Window functions | [#35](https://github.com/alberttwong/redis-adbc-driver/pull/35) |
| [#20](https://github.com/alberttwong/redis-adbc-driver/issues/20) `MERGE`, `UPDATE … FROM`, `DELETE … USING` | [#29](https://github.com/alberttwong/redis-adbc-driver/pull/29) |
| [#21](https://github.com/alberttwong/redis-adbc-driver/issues/21) Temporary tables | [#30](https://github.com/alberttwong/redis-adbc-driver/pull/30) |
| [#22](https://github.com/alberttwong/redis-adbc-driver/issues/22) Renaming views | [#27](https://github.com/alberttwong/redis-adbc-driver/pull/27) |
| [#23](https://github.com/alberttwong/redis-adbc-driver/issues/23) `INSERT … (SELECT)`, `TRUNCATE`, `DROP … CASCADE` | [#25](https://github.com/alberttwong/redis-adbc-driver/pull/25) |
| [#24](https://github.com/alberttwong/redis-adbc-driver/issues/24) `ROUND`, `SUBSTRING`, `NULLIF` and other scalar functions | [#28](https://github.com/alberttwong/redis-adbc-driver/pull/28) |
| [#31](https://github.com/alberttwong/redis-adbc-driver/issues/31), [#32](https://github.com/alberttwong/redis-adbc-driver/issues/32) `SELECT DISTINCT` / `DISTINCT ON`, qualified `t.*` | [#39](https://github.com/alberttwong/redis-adbc-driver/pull/39) |
| [#33](https://github.com/alberttwong/redis-adbc-driver/issues/33) `CONCAT` returned NULL for any NULL argument | [#34](https://github.com/alberttwong/redis-adbc-driver/pull/34) |
| [#36](https://github.com/alberttwong/redis-adbc-driver/issues/36) Wrong results: rounded constants pushed into the index (`int_col > 1.5`) | [#40](https://github.com/alberttwong/redis-adbc-driver/pull/40) |
| [#37](https://github.com/alberttwong/redis-adbc-driver/issues/37) Slow literal `IN` lists over 1,000 values (66 s → 1 s) | [#41](https://github.com/alberttwong/redis-adbc-driver/pull/41) |
| [#43](https://github.com/alberttwong/redis-adbc-driver/issues/43) Column `DEFAULT`s accepted but never applied | [#57](https://github.com/alberttwong/redis-adbc-driver/pull/57) |
| [#44](https://github.com/alberttwong/redis-adbc-driver/issues/44), [#45](https://github.com/alberttwong/redis-adbc-driver/issues/45), [#50](https://github.com/alberttwong/redis-adbc-driver/issues/50) `TRY_CAST`, `%` on NUMERIC, `DATEADD` / `DATEDIFF` (dbt's `dateadd`, `datediff`, `last_day`, `date_spine`) | [#56](https://github.com/alberttwong/redis-adbc-driver/pull/56) |
| [#46](https://github.com/alberttwong/redis-adbc-driver/issues/46), [#47](https://github.com/alberttwong/redis-adbc-driver/issues/47) `STRING_AGG`, `BOOL_OR`, `ANY_VALUE`, statistics and percentiles; `FILTER`, `IGNORE NULLS`, frame `EXCLUDE` (dbt's `listagg`, `bool_or`, `any_value`) | [#62](https://github.com/alberttwong/redis-adbc-driver/pull/62) |
| [#48](https://github.com/alberttwong/redis-adbc-driver/issues/48) `GROUPING SETS`, `ROLLUP`, `CUBE` | [#59](https://github.com/alberttwong/redis-adbc-driver/pull/59) |
| [#49](https://github.com/alberttwong/redis-adbc-driver/issues/49) Regular expressions | [#61](https://github.com/alberttwong/redis-adbc-driver/pull/61) |
| [#51](https://github.com/alberttwong/redis-adbc-driver/issues/51) `RETURNING`, `UPDATE … SET (a, b) = (…)` | [#58](https://github.com/alberttwong/redis-adbc-driver/pull/58) |
| [#52](https://github.com/alberttwong/redis-adbc-driver/issues/52) `WITH RECURSIVE`, `LATERAL`, `ANY` / `ALL`, `NATURAL JOIN`, `GENERATE_SERIES` | [#68](https://github.com/alberttwong/redis-adbc-driver/pull/68) |
| [#53](https://github.com/alberttwong/redis-adbc-driver/issues/53) JSON functions | [#64](https://github.com/alberttwong/redis-adbc-driver/pull/64) |
| [#54](https://github.com/alberttwong/redis-adbc-driver/issues/54) Renamed tables keep their old key prefix (opt-in fix: `rename_rekey`) | [#69](https://github.com/alberttwong/redis-adbc-driver/pull/69) |
| [#72](https://github.com/alberttwong/redis-adbc-driver/issues/72) `COMMENT ON` (dbt's `persist_docs`) | [#73](https://github.com/alberttwong/redis-adbc-driver/pull/73) |
| [#74](https://github.com/alberttwong/redis-adbc-driver/issues/74) `WHERE false` / `LIMIT 0` ran the whole query (dbt's contract checks, `--empty`: 5 s → 2 ms on `dim_zones`) | [#77](https://github.com/alberttwong/redis-adbc-driver/pull/77) |
| [#75](https://github.com/alberttwong/redis-adbc-driver/issues/75) Column-level `CHECK` / `REFERENCES` didn't parse; `CHECK` wasn't enforced | [#76](https://github.com/alberttwong/redis-adbc-driver/pull/76) |
| [#78](https://github.com/alberttwong/redis-adbc-driver/issues/78) Unknown functions were only caught when a row was evaluated, so they passed contract checks and `--empty` | [#79](https://github.com/alberttwong/redis-adbc-driver/pull/79) |
| [#82](https://github.com/alberttwong/redis-adbc-driver/issues/82) Wrong results: a table re-created after a concurrent `DROP` read the dropped table's leftover rows | [#99](https://github.com/alberttwong/redis-adbc-driver/pull/99) |
| [#83](https://github.com/alberttwong/redis-adbc-driver/issues/83), [#101](https://github.com/alberttwong/redis-adbc-driver/issues/101) `SUM` / `AVG` of DOUBLE varied with row order and pushdown mode, and gave `NaN` with `aggregate_pushdown=all` on a cluster | [#107](https://github.com/alberttwong/redis-adbc-driver/pull/107) |
| [#84](https://github.com/alberttwong/redis-adbc-driver/issues/84), [#88](https://github.com/alberttwong/redis-adbc-driver/issues/88), [#90](https://github.com/alberttwong/redis-adbc-driver/issues/90) Timestamp text kept trailing zeros; no `AT TIME ZONE` / `convert_timezone()`; `to_char` printed `WW`, `J`, … literally (dbt_utils' `generate_surrogate_key`, dbt_date) | [#97](https://github.com/alberttwong/redis-adbc-driver/pull/97) |
| [#85](https://github.com/alberttwong/redis-adbc-driver/issues/85) Row values, `(k1, k2) IN (…)` (dbt's delete+insert with a list `unique_key`) | [#98](https://github.com/alberttwong/redis-adbc-driver/pull/98) |
| [#86](https://github.com/alberttwong/redis-adbc-driver/issues/86), [#87](https://github.com/alberttwong/redis-adbc-driver/issues/87), [#94](https://github.com/alberttwong/redis-adbc-driver/issues/94) A 5–10 s client read timeout; a killed `rename_rekey` rename blocked retries; incomplete ACL docs | [#100](https://github.com/alberttwong/redis-adbc-driver/pull/100) |
| [#89](https://github.com/alberttwong/redis-adbc-driver/issues/89) Trigonometric functions (dbt_utils' `haversine_distance`) | [#107](https://github.com/alberttwong/redis-adbc-driver/pull/107) |
| [#91](https://github.com/alberttwong/redis-adbc-driver/issues/91), [#92](https://github.com/alberttwong/redis-adbc-driver/issues/92) Multi-action `ALTER TABLE` (`on_schema_change`); `BEGIN` / `COMMIT` / `SET` (hooks outside the transaction) | [#96](https://github.com/alberttwong/redis-adbc-driver/pull/96) |
| [#93](https://github.com/alberttwong/redis-adbc-driver/issues/93) `VARCHAR(n)` / `CHAR(n)` lengths were ignored | [#95](https://github.com/alberttwong/redis-adbc-driver/pull/95) |
| [#102](https://github.com/alberttwong/redis-adbc-driver/issues/102) Wrong results: `t.col` inside `(… from t x …)` read the inner row | [#108](https://github.com/alberttwong/redis-adbc-driver/pull/108) |
| [#103](https://github.com/alberttwong/redis-adbc-driver/issues/103), [#105](https://github.com/alberttwong/redis-adbc-driver/issues/105) Casts to a lower time precision truncated; no session time zone | [#106](https://github.com/alberttwong/redis-adbc-driver/pull/106) |
| [#104](https://github.com/alberttwong/redis-adbc-driver/issues/104) Data loss: `TRUNCATE … RESTART IDENTITY` during a concurrent write | [#109](https://github.com/alberttwong/redis-adbc-driver/pull/109) |
| [#110](https://github.com/alberttwong/redis-adbc-driver/issues/110) Rows whose DOUBLE column is `NaN` were written but never returned | [#116](https://github.com/alberttwong/redis-adbc-driver/pull/116) |
| [#111](https://github.com/alberttwong/redis-adbc-driver/issues/111) Wrong results: schema-qualified column references (`s.t.col`) ignored the schema | [#115](https://github.com/alberttwong/redis-adbc-driver/pull/115) |
| [#112](https://github.com/alberttwong/redis-adbc-driver/issues/112) `GROUP BY` didn't reject ungrouped outer columns inside subqueries | [#117](https://github.com/alberttwong/redis-adbc-driver/pull/117) |
| [#113](https://github.com/alberttwong/redis-adbc-driver/issues/113) Fractional-second precisions other than 0, 3, 6 and 9 snapped to 3, 6 or 9 digits | [#118](https://github.com/alberttwong/redis-adbc-driver/pull/118) |

## Known limitations

The driver runs the SQL that dbt and its cross-database macros generate, and
the dbt features above all work. Three limits come from the design:

- **No transactions.** Every statement autocommits, so a run that stops in
  the middle of a materialization can leave a `__dbt_tmp` or `__dbt_backup`
  relation behind. dbt drops those at the start of the next run of that
  model. The run's temporary tables (`pg_temp_N`) stay until the driver's
  2-minute heartbeat for that connection runs out; the next connection then
  removes them. Ctrl-C and `--fail-fast` cancel the running statements,
  which leaves the same kind of remains: each statement stops at its next
  Redis command, and the rows it already wrote stay until the next run
  drops its relation. A cancelled `rename_rekey` rename leaves the table as
  it was. Two things don't stop early: work the driver does in memory (a
  join, say) runs until it next calls Redis
  ([driver #150](https://github.com/alberttwong/redis-adbc-driver/issues/150)),
  and v0.0.11 reads a streamed `dbt show` result to the end
  ([driver #142](https://github.com/alberttwong/redis-adbc-driver/issues/142),
  fixed after v0.0.11).
- **SQL models only.** dbt Python models aren't supported, and neither are
  materialized views (`materialized='materialized_view'` stops with a clear
  error).
- **No grants.** Redis controls access per user with ACLs (key patterns and
  commands), not SQL privileges on tables, so a `grants` config is skipped
  with a warning.

## Access control

dbt can run as a Redis ACL user (`username` / `password` in `profiles.yml`).
The commands and key patterns the driver needs, per feature, and a read-only
user recipe are in the
[driver's README](https://github.com/alberttwong/redis-adbc-driver#server-requirements).
A read-only user can run `dbt show`, the data tests
and `docs generate`. Unit tests and snapshots create temporary tables, which
need `INCRBY` on the driver's metadata keys, so they fail for a read-only
user (dbt reports the unit-test failure as a data-type mismatch).

## Looking at the data in Redis

Each row is a HASH, and each table has a RediSearch index. On a cluster, add
`-c` to `redis-cli` so it follows the key to its shard:

```bash
docker exec redis-dbt-taxi redis-cli HGETALL raw:yellow_tripdata:1
```

```bash
docker exec redis-dbt-taxi redis-cli FT.INFO idx:raw:yellow_tripdata
```

Tables built by dbt's rename-swap keep the row key prefix and index of the
`__dbt_tmp` table they were created as. `ALTER TABLE … RENAME` only changes
metadata, and the driver never gives a new table a prefix another table had
(so a dropped or truncated table's leftover keys can't reach it). Each build's
`__dbt_tmp` therefore gets the next free one: `…__dbt_tmp:`, `…__dbt_tmp~2:`,
`~3` and so on. A table also takes the next names when an index the driver
didn't create already has its index's name (an application's
`idx:taxi:users`, say), and leaves that index and its HASHes alone. To get
keys named after the table, set `rename_rekey: true` in
`profiles.yml`. Each rename then moves the table's rows to keys under its own
name (`schema:table:` on the first build, `schema:table~N:` after that). For a
rebuilt table that costs one copy of its new rows: the adapter drops the old
table instead of moving it to `__dbt_backup` first.
Either way, a table's current prefix and index are in its metadata:

```bash
docker exec redis-dbt-taxi redis-cli GET 'adbc:{meta}:table:taxi_marts:agg_daily_revenue'
```

The metadata also holds the comments `persist_docs` writes. They're easier to
read through `information_schema`:

```bash
uv run dbt show --inline "select table_name, comment from information_schema.tables where table_schema = 'taxi_marts'"
```

To watch the `FT.AGGREGATE` / `HMGET` traffic while dbt runs:

```bash
docker exec -it redis-dbt-taxi redis-cli MONITOR
```

## Data

NYC TLC yellow taxi trip records for January 2019, as CSV, from the
[DataTalksClub mirror](https://github.com/DataTalksClub/nyc-tlc-data). The TLC
itself now publishes only Parquet. Zone lookup:
[TLC taxi zones](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
