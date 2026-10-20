# Redis adapter integration for dbt v2

**Redis v2 support is not implemented yet.** This directory provides a native
Redis profile fixture, a smoke runner, and the implementation plan. A passing
runner unit test is not evidence that dbt v2 can connect to Redis.

The Python v1 adapter, its dependencies, driver tooling, and NYC taxi example
live in [`../v1/`](../v1/README.md). The v2 runner uses Python 3.10+ and the
standard library only; it does not install or import the v1 adapter.

## Engine implementation

dbt v2 adapters are compiled into the Rust engine, as described in the
[adapter creation guide](https://docs.getdbt.com/guides/adapter-creation-v2).
The engine changes belong in [`alberttwong/dbt`](https://github.com/alberttwong/dbt),
a fork of [`dbt-labs/dbt`](https://github.com/dbt-labs/dbt).
[`upstream.json`](upstream.json) records the source baseline examined for this
work. There is no Redis implementation branch in the fork yet.

```sh
git clone https://github.com/alberttwong/dbt.git redis-dbt-engine
cd redis-dbt-engine
git remote add upstream https://github.com/dbt-labs/dbt.git
git switch -c codex/redis-adapter 4bb4caa4ae1e7f4354c7817093a55514c6cbea41
```

Read that checkout's `AGENTS.md`, `.agents/adapters.md`, and `CONTRIBUTING.md`
before making engine changes. Its architecture has evolved from some paths in
the public adapter guide; use the pinned source as the implementation reference.

The integration work is tracked in
[issue #69](https://github.com/alberttwong/redis-dbt-adapter-with-project/issues/69).
This directory replaces the need for a separate `redis-dbt-v2-adapter` integration
repository. That repository remains empty.

## Smoke checks

Pass the **v2 executable explicitly**. Do not pass `v1/.venv/bin/dbt`, which is
Python Core 1.x. From this repository's root:

```sh
# Parse only; no Redis connection or driver download is performed by the runner.
python3 v2/smoke.py --dbt /absolute/path/to/dbt-v2

# After the Rust Redis adapter is available, use a test Redis instance.
export REDIS_ADBC_DRIVER=/absolute/path/to/libadbc_driver_redis.dylib
export REDIS_URI=redis://localhost:6380/0
python3 v2/smoke.py --dbt /absolute/path/to/dbt-v2 --build
```

Use the appropriate `.so` or `.dll` on other platforms. Use `REDIS_USERNAME` and
`REDIS_PASSWORD` for credentials; they are not command arguments. The driver
library is distributed separately. The existing `v1/scripts/download_driver.sh`
can fetch it into `v1/driver/` using the existing GitHub access requirements.
Keep `REDIS_ADBC_DRIVER` absolute because the runner copies the fixture to a
temporary directory. The [v1 driver guide](../v1/README.md#requirements) describes
server and driver requirements. The v2 profile fields are a **proposed contract**
for the engine implementation; the stock binary does not recognize them yet.

The runner checks the executable's major version, then parses using
`type: redis_adbc`. It fails on an unregistered adapter rather than substituting
another warehouse. For `--build`, it creates a random `dbt_v2_smoke_*` schema,
performs a full-refresh build followed by an incremental build, checks fresh
`run_results.json` artifacts, and drops only its own schema afterward. A failed
build still attempts cleanup; cleanup failure returns a failure and prints the
schema name for manual removal. Temporary project files, logs, and artifacts
are removed when the runner exits. dbt output is streamed to the console.

The fixture covers seed loading, an ephemeral model, a table, a view, generic
tests, and incremental `delete+insert`. Three seed rows must remain three rows
after both builds, and totals must reconcile. It has no package dependencies,
does not download taxi data, and does not use the v1 taxi schemas.

The runner enables `DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes` for an experimental
Redis engine build. This does not register a missing adapter.

## Current blocker and validation scope

The locked v1 dependencies include a `dbt-core-experimental-parser` executable
reporting `dbt-oss 2.0.5`. On the unmodified engine it rejects the fixture with
`unknown variant redis_adbc` while loading `profiles.yml`, before parsing models
or connecting to Redis. The `dbt parse --use-v2-parser` path has the same blocker.
Simply relaxing the v1 `<2` dependency constraints cannot fix this.

Run the runner unit tests without a database:

```sh
python3 -m unittest discover -s v2/tests -v
```

CI runs those unit tests separately from the v1 functional suite. Full v2
execution is not enabled in CI until an engine build containing Redis support
exists. See the [implementation checklist](IMPLEMENTATION.md) for the remaining
work, including features outside this initial smoke fixture.
