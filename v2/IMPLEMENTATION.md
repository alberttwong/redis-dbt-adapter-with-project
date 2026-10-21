# Redis v2 implementation checklist

Baseline: [`4bb4caa`](https://github.com/dbt-labs/dbt/tree/4bb4caa4ae1e7f4354c7817093a55514c6cbea41).
Upstream changes should be contributed from the [`alberttwong/dbt`](https://github.com/alberttwong/dbt)
fork. Keep the existing Python package and its `<2` dependencies in `v1/`.

## Register the adapter in the engine

- [x] Add the `redis_adbc` adapter identity to `dbt-adapter-core` and the
  typed profile variant to `dbt-schemas/src/schemas/profiles.rs`.
- [x] Map the profile fields to ADBC options in `dbt-auth`, loading the Redis
  library through the existing `dbt-adbc` driver-loading facilities. Register
  its backend as required; do not introduce a Python adapter dependency.
- [x] Cover all exhaustive adapter matches, experimental profile gating,
  profile setup, protocol adapter identities, and SQL dialect handling affected
  by the new identity. Compile and test the affected crates in the fork.

Implemented connection mapping, derived from the v1 adapter:

| Profile field | Driver configuration |
| --- | --- |
| `driver` | Absolute local shared-library path; driver loading, not a database option |
| `uri` | `uri` (Redis or TLS Redis URI) |
| `username`, `password` | Separate ADBC credential options |
| `schema` | `adbc.redis.default_schema` |
| `database` | Single catalog `redis`; validate rather than silently ignoring another catalog |
| `time_zone` | `adbc.redis.time_zone` |

Other v1 options (`aggregate_pushdown`, `rename_rekey`, timeouts, and
`driver_options`) need an explicit v2 validation and precedence policy. Preserve
credential redaction in debug output and errors. Test invalid catalog, missing
driver, authentication errors, and TLS configuration.

## Port relation, metadata, and SQL behavior

- [x] Render relations as `schema.table`, omitting the `redis` catalog. Preserve
  explicit quoting and identifier case. Temporary relations are unqualified.
- [ ] Implement schema, relation, column, and catalog introspection through the
  driver. The v1 implementation uses ADBC `GetObjects` and Arrow metadata;
  avoid assuming another warehouse's information-schema layout.
- [ ] Port the necessary Jinja macros from `v1/adapter/dbt/include/redis_adbc/`
  into the engine's macro assets, using its required review and macro tests.
  Keep the `redis_adbc__` dispatch name so package overrides can be reused.
- [x] Preserve autocommit behavior: Redis does not support SQL transactions or
  rollback. Do not send `BEGIN`/`COMMIT` as if the driver were PostgreSQL.
- [x] Define Arrow/SQL type mapping, seed ingestion or binding behavior, and
  adapter response counts. The v1 driver uses `?` placeholders.

## Prove execution before claiming support

- [x] Pass `v2/smoke.py --dbt <redis-enabled-engine> --build`, including the
  second incremental build and cleanup.
- [x] Add a manual CI workflow that builds an engine at a pinned Redis
  implementation commit and runs the fixture with the pinned driver.
- [ ] Verify the first native Linux CI run after merging the workflow.
- [ ] Validate the full NYC taxi SQL project, packages and strict v2 parsing,
  source loading, contracts, persisted docs, snapshots, `merge`, `microbatch`,
  and empty builds. Keep its Python model and custom `adapter.load_csv_file`
  loader as explicit migration gaps until replacements are implemented.
- [ ] Check v2 artifact and CLI behavior before reusing the v1 CI result checks.
  Port applicable functional scenarios; the Python `dbt-tests-adapter` suite
  cannot validate a compiled v2 adapter by itself.
- [ ] Document unsupported features and the migration commands; retain v1
  support while v2 is developed. Only then update the support statement and
  close issue #69.

## Validated milestone

Native macOS arm64 smoke passed with dbt-oss 2.0.8, Redis 8.6.2, and Redis ADBC
v0.0.14. The pinned engine implements native profiles, local driver loading,
schema/relation/column introspection, table and view materialization, seed SQL
literal binding, and incremental delete+insert. Both builds passed all five
tests and dropped the temporary schema. Python models and microbatch remain
unsupported in this experimental adapter. Catalog export and the other v1
macros still need porting and validation.
