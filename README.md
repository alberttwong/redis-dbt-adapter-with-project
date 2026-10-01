# dbt on Redis: NYC taxi trips

A dbt Core project that tests the DBT Redis adapter which is built on the
[Redis ADBC driver](https://github.com/alberttwong/redis-adbc-driver). It does
three things:

- loads the NYC TLC yellow-taxi trips CSV into Redis,
- transforms it with ordinary dbt SQL: views, tables, an incremental MERGE
  fact table, a snapshot, joins, window functions, CTEs and `QUALIFY`,
- tests and documents it with dbt's standard commands.

dbt's own default materializations do the work: tables, views, incremental
models (temporary tables plus `MERGE` or delete+insert) and snapshots. The SQL
dbt generates runs on the driver unchanged.

```
dbt  ──►  dbt-redis-adbc (adapter/)  ──►  adbc_driver_manager  ──►  libadbc_driver_redis  ──►  Redis 8
          Python + Jinja                  ADBC DB-API              SQL → FT.AGGREGATE / HASH
```

## Quick start

Requirements: Docker, [uv](https://docs.astral.sh/uv/) (it provides Python
3.10–3.13 for dbt), Go 1.26+ and a C toolchain (to build the driver).

```bash
make setup
```

`make setup` does four things:

- runs `uv sync`
- builds the driver into `driver/`. It's pinned to driver commit `f2b45ab`; override it with `DRIVER_VERSION`.
- downloads the CSV into `data/`
- starts Redis **8.6.2**, the version Redis Cloud runs, on port 6380

```bash
make all
```

`make all` runs `dbt debug`, `seed`, `run-operation load_raw_trips`, `build`
and `docs generate`. To try the incremental model and the snapshot:

```bash
make incremental-demo
```

```bash
make snapshot-demo
```

Use `make docs-serve` to browse the docs and lineage graph.

Redis is published on **6380** so it doesn't collide with a local Redis on
6379. Override the connection with `REDIS_URI` (for example
`rediss://default:<pw>@host:port/0` for Redis Cloud) and the driver location
with `REDIS_ADBC_DRIVER`.

## dbt commands this project exercises

| Command | What happens in Redis |
|-|-|
| `dbt debug` | Opens an ADBC connection; the driver checks that the Query Engine is available (`FT._LIST`) |
| `dbt seed` | 4 lookup CSVs (zones, payment types, rate codes, vendors), loaded with ADBC bulk ingest; reloads use `TRUNCATE` |
| `dbt run-operation load_raw_trips` | Streams the 134 MB gzipped CSV with pyarrow, keeps every 50th row (~153k trips across January), adds `trip_id` (the trip's row number in the file), and bulk-ingests it into `raw.yellow_tripdata` in about 6 s |
| `dbt run` | 5 views and 8 tables, rebuilt with dbt's create-then-`ALTER … RENAME` swap; plus 1 incremental model, built by `CREATE TEMPORARY TABLE` then `MERGE` |
| `dbt snapshot` | `zones_snapshot`: SCD type 2 history of the zone lookup (check strategy), written by dbt's snapshot `MERGE` |
| `dbt test` / `dbt build` | 48 data tests (`unique`, `not_null`, `accepted_values`, `relationships`, custom generic `non_negative` / `in_range`, 2 singular tests) and 2 unit tests |
| `dbt show`, `dbt compile`, `dbt ls` | Previews, inline queries, and the analysis in `analyses/` |
| `dbt docs generate` | Catalog built from ADBC `GetObjects` (column types, tables vs views) |

A clean `make all` takes about 80 s on a laptop. It ends with 68 passes and 1
**intended** warning: the source test flags a $623,261.66 fare in the raw
data, which staging filters out.

## Project layout

```
models/
  staging/        views over raw + seeds: rename, type, filter, derive hour/weekday/duration
  intermediate/   int_trips_enriched: trips ⋈ zones (×2) ⋈ payment types ⋈ rate codes ⋈ vendors
  marts/          fct_trips (incremental MERGE), dim_zones, agg_daily_revenue (7-day rolling
                  average, LAG, RANK), agg_top_pickup_zones (RANK … QUALIFY), agg_hourly_demand,
                  agg_borough_flows, agg_payment_mix, agg_airport_trips
snapshots/        zones_snapshot (SCD type 2 of the zone lookup)
seeds/            taxi_zone_lookup, payment_types, rate_codes, vendors
macros/           load_raw_trips and rename_zone (run-operations), day_part
tests/            generic (non_negative, in_range) and singular tests
analyses/         top_pickup_zones_by_day_part
adapter/          the dbt-redis-adbc adapter package (installed editable by uv)
scripts/          build_driver.sh, download_data.sh
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

## What the adapter does

dbt only connects to a database through an adapter package, and there is no
generic ADBC adapter. `adapter/` is a small one: about 520 lines of Python and
55 lines of macros. The driver runs the SQL of dbt's default macros and
materializations, so the adapter covers what isn't SQL:

| Area | Adapter |
|-|-|
| Connection | `adbc_driver_manager` DB-API, autocommit (the driver has no transactions, so `BEGIN`/`COMMIT` are no-ops) |
| Metadata | Relations, columns and the docs catalog come from ADBC `GetObjects` |
| Temporary tables | `make_temp_relation` renders them unqualified (a schema-qualified name always means a permanent table), and their columns are looked up under `pg_temp` |
| Incremental strategies | `append`, `delete+insert` (the default with a `unique_key`) and `merge` |
| Loading | Seeds and the raw CSV go through Arrow bulk ingest, which is much faster than INSERTs |
| Cross-database macros | dbt-core's defaults work natively except two: `safe_cast` uses the driver's `TRY_CAST`, and `listagg` with `limit_num` raises a clear error (it needs arrays). `tests/assert_cross_db_macros.sql` checks them all |
| Model contracts | An enforced contract creates the table from its DDL, then inserts the rows (as on dbt-postgres). `not_null` is enforced by the driver; `primary_key` and `unique` are accepted but not enforced; `check` and `foreign_key` are skipped with a warning |
| Small dialect bits | `?` bind parameters, `CURRENT_TIMESTAMP`, and a subquery wrapper for `dbt show --limit` |

Profile options (`profiles.yml`): `driver`, `uri`, `username`, `password`,
`database` (always `redis`), `schema`, `threads`, `aggregate_pushdown`
(`exact` / `all` / `none`), and `rename_rekey` (see
[Looking at the data in Redis](#looking-at-the-data-in-redis)).

## Driver issues found along the way

Building this project turned up these issues, all filed on
[alberttwong/redis-adbc-driver](https://github.com/alberttwong/redis-adbc-driver/issues).
All of them are fixed on the pinned driver.

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

## Known limitations

The driver now runs the SQL that dbt and its cross-database macros generate.
What's left is in the adapter, plus one driver feature:

| Doesn't work yet | Effect in dbt | Issue |
|-|-|-|
| The `microbatch` incremental strategy | `not valid for this adapter` | [#7](https://github.com/alberttwong/redis-dbt-project/issues/7) |
| `persist_docs` | Fails the model; the driver has no `COMMENT ON` yet ([driver #72](https://github.com/alberttwong/redis-adbc-driver/issues/72)) | [#9](https://github.com/alberttwong/redis-dbt-project/issues/9) |
| `grants` | Fails the model; Redis controls access with ACLs, not `GRANT` | [#10](https://github.com/alberttwong/redis-dbt-project/issues/10) |

Two limits come from the design rather than a missing feature:

- **No transactions.** Every statement autocommits, so a run that stops in
  the middle of a materialization can leave a `__dbt_tmp` or `__dbt_backup`
  relation behind. dbt drops those at the start of the next run of that
  model.
- **SQL models only.** dbt Python models aren't supported.

## Looking at the data in Redis

Each row is a HASH, and each table has a RediSearch index:

```bash
docker exec redis-dbt-taxi redis-cli HGETALL raw:yellow_tripdata:1
```

```bash
docker exec redis-dbt-taxi redis-cli FT.INFO idx:raw:yellow_tripdata
```

Tables built by dbt's rename-swap keep the row key prefix and index of the
`__dbt_tmp` table they were created as. `ALTER TABLE … RENAME` only changes
metadata, and the driver never reuses a prefix, so later builds get
`…__dbt_tmp~2`, `~3` and so on. To keep key names matching the tables, set
`rename_rekey: true` in `profiles.yml`. Each rename then moves the table's
rows to its own name's keys, which costs a copy of every row on each build.
Either way, a table's current prefix and index are in its metadata:

```bash
docker exec redis-dbt-taxi redis-cli GET 'adbc:{meta}:table:taxi_marts:agg_daily_revenue'
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
