# dbt on Redis: NYC taxi trips

A dbt Core project that runs entirely on Redis 8, through the
[Redis ADBC driver](https://github.com/alberttwong/redis-adbc-driver). It does
three things:

- loads the NYC TLC yellow-taxi trips CSV into Redis,
- transforms it with ordinary dbt SQL models (views, tables, an incremental
  fact table, joins, CTEs, HAVING, subqueries),
- tests and documents it with dbt's standard commands.

```
dbt  ──►  dbt-redis-adbc (adapter/)  ──►  adbc_driver_manager  ──►  libadbc_driver_redis  ──►  Redis 8
          Python + Jinja                  ADBC DB-API              SQL → FT.AGGREGATE / HASH
```

## Quick start

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Go 1.26+ and a C
toolchain (to build the driver).

```bash
make setup
```

`make setup` runs `uv sync`, builds the driver into `driver/` (pinned to
`54b83af`; override with `DRIVER_VERSION`), downloads
the CSV into `data/`, and starts Redis 8.4 on port 6380.

```bash
make all
```

`make all` runs `dbt debug`, `seed`, `run-operation load_raw_trips`, `build`
and `docs generate`.

```bash
make incremental-demo
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
| `dbt seed` | 4 lookup CSVs (zones, payment types, rate codes, vendors) → tables via ADBC bulk ingest |
| `dbt run-operation load_raw_trips` | Streams the 134 MB gzipped CSV with pyarrow, keeps every 50th row (~153k trips across January), adds `trip_id` (the trip's row number in the file), and bulk-ingests it into `raw.yellow_tripdata` in about 6 s |
| `dbt run` | 5 views, 7 tables (CTAS + `ALTER TABLE … RENAME` swap), 1 incremental model |
| `dbt test` / `dbt build` | 43 data tests (`unique`, `not_null`, `accepted_values`, `relationships`, custom generic `non_negative` / `in_range`, 2 singular tests) and 2 unit tests |
| `dbt run --full-refresh`, incremental runs | delete+insert on `trip_id`, reprocessing the 6 hours before the latest pickup |
| `dbt show`, `dbt compile`, `dbt ls` | Previews, inline queries, and the analysis in `analyses/` |
| `dbt docs generate` | Catalog built from ADBC `GetObjects` (column types, tables vs views) |

A clean `make all` takes about 90 s on a laptop. It ends with 61 passes and 1
**intended** warning: the source test flags a $623,261.66 fare in the raw
data, which staging filters out.

## Project layout

```
models/
  staging/        views over raw + seeds: rename, type, filter, derive hour/day part
  intermediate/   int_trips_enriched: trips ⋈ zones (×2) ⋈ payment types ⋈ rate codes ⋈ vendors
  marts/          fct_trips (incremental), dim_zones, agg_daily_revenue, agg_hourly_demand,
                  agg_borough_flows, agg_payment_mix, agg_airport_trips
seeds/            taxi_zone_lookup, payment_types, rate_codes, vendors
macros/           load_raw_trips (run-operation), day_part, round_to
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
| `lookback_hours` | `6` | Hours before the latest loaded pickup that each incremental run reprocesses |

## Why there's an adapter

dbt only connects to a database through an adapter package, and there is no
generic ADBC adapter. `adapter/` is a thin one: about 500 lines of Python
plus a few macros. It sends every query through the driver unchanged, and it
covers what dbt expects but the driver doesn't provide:

| dbt expects | Driver (54b83af) | Adapter does |
|-|-|-|
| Transactions (`BEGIN`/`COMMIT`) | Autocommit only | No-op begin/commit; connects with `autocommit=True` |
| Table and column metadata | ADBC `GetObjects` | `list_relations`, `get_columns_in_relation` and the docs catalog use `GetObjects` |
| View rename-swap (`ALTER … RENAME`) | `ALTER TABLE` finds tables only ([#22](https://github.com/alberttwong/redis-adbc-driver/issues/22)) | Views use `CREATE OR REPLACE VIEW`; tables keep dbt's default swap |
| Temporary tables for incremental | Not supported ([#21](https://github.com/alberttwong/redis-adbc-driver/issues/21)) | Stages into a regular `__dbt_tmp` table |
| `delete+insert` incremental | Large `IN (SELECT …)` is slow ([#17](https://github.com/alberttwong/redis-adbc-driver/issues/17)) | Finds matched keys with a join and deletes only those |
| `TRUNCATE` | Not supported ([#23](https://github.com/alberttwong/redis-adbc-driver/issues/23)) | `DELETE FROM` |
| `DROP SCHEMA` on a non-empty schema | Fails, no `CASCADE` ([#23](https://github.com/alberttwong/redis-adbc-driver/issues/23)) | Drops the schema's tables first |
| Batched parameterized `INSERT` for seeds | Works (fixed in [#15](https://github.com/alberttwong/redis-adbc-driver/pull/15)) | Seeds load through Arrow bulk ingest, which is much faster |
| Loading a large CSV | n/a | `adapter.load_csv_file` streams the file with pyarrow into ADBC ingest |

Profile options (`profiles.yml`): `driver`, `uri`, `username`, `password`,
`database` (always `redis`), `schema`, `threads`, and `aggregate_pushdown`
(`exact` / `all` / `none`).

## Working within the driver's SQL

The models use the driver's SQL directly: `EXTRACT`, interval arithmetic
(`dropoff - pickup`, `max(pickup) - interval '6 hours'`), `CASE`, joins,
CTEs, `HAVING`, and scalar subqueries. One function is still missing:

- **Rounding:** there's no `ROUND` yet
  ([#24](https://github.com/alberttwong/redis-adbc-driver/issues/24)), so
  `round_to(expr, s)` is `CAST(expr AS NUMERIC(18, s))`.

## Driver issues

All are filed on [alberttwong/redis-adbc-driver](https://github.com/alberttwong/redis-adbc-driver/issues):

| Issue | Effect on this project |
|-|-|
| [#13](https://github.com/alberttwong/redis-adbc-driver/issues/13) bound string parameters read freed memory | Fixed in #15 |
| [#17](https://github.com/alberttwong/redis-adbc-driver/issues/17) large `IN (SELECT …)` is O(n×m): 57 s for 82k keys against 4.7 s for a join | Incremental runs match keys with a join first |
| [#18](https://github.com/alberttwong/redis-adbc-driver/issues/18) correlated `EXISTS` runs once per outer row: 28 s against an empty table | Avoided |
| [#19](https://github.com/alberttwong/redis-adbc-driver/issues/19) window functions | No `row_number()` de-duplication; blocks `dbt snapshot` |
| [#20](https://github.com/alberttwong/redis-adbc-driver/issues/20) `MERGE`, `UPDATE … FROM`, `DELETE … USING` | Blocks `dbt snapshot` and the `merge` incremental strategy |
| [#21](https://github.com/alberttwong/redis-adbc-driver/issues/21) temporary tables | Adapter stages into `__dbt_tmp` tables |
| [#22](https://github.com/alberttwong/redis-adbc-driver/issues/22) renaming views | Adapter uses `CREATE OR REPLACE VIEW` |
| [#23](https://github.com/alberttwong/redis-adbc-driver/issues/23) `INSERT … (SELECT)`, `TRUNCATE`, `DROP SCHEMA … CASCADE` | Adapter works around all three |
| [#24](https://github.com/alberttwong/redis-adbc-driver/issues/24) `ROUND`, `SUBSTRING`, `NULLIF` and other scalar functions | `round_to` macro |

## Looking at the data in Redis

Each row is a HASH, and each table has a RediSearch index:

```bash
docker exec redis-dbt-taxi redis-cli HGETALL raw:yellow_tripdata:1
```

```bash
docker exec redis-dbt-taxi redis-cli FT.INFO idx:taxi_marts:fct_trips
```

Tables built by dbt's rename-swap keep the row key prefix and index of the
`__dbt_tmp` table they were created as. `ALTER TABLE … RENAME` only changes
metadata, and the driver never reuses a prefix, so later builds get
`…__dbt_tmp~2`, `~3` and so on. Look up a table's current prefix and index
in its metadata:

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
