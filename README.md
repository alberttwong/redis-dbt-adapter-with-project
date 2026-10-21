# Redis adapters for dbt

This repository keeps dbt v1 and v2 work together, with separate dependencies,
projects, and test resources.

| Directory | Purpose | Status |
| --- | --- | --- |
| [`v1/`](v1/README.md) | Python `dbt-redis-adbc` adapter, NYC taxi example, driver tooling, and functional tests | Supports dbt Core 1.10 and later 1.x releases; the example requires 1.10.8+ |
| [`v2/`](v2/README.md) | Native v2 integration fixture, smoke runner, and implementation plan | Experimental fork: native smoke builds pass; requires a custom engine |

## Run the v1 example

Run the existing commands from `v1/`:

```sh
cd v1
make setup
make all
```

See the [v1 guide](v1/README.md) for connection configuration, requirements,
supported features, and the NYC taxi demos. The installable adapter package is
in [`v1/adapter/`](v1/adapter/README.md). If you had a virtual environment from
the former root layout, recreate it from `v1/` with `uv sync --reinstall` and
refresh local package links with `uv run dbt deps`.

## Develop v2 support

dbt v2 compiles adapters into its Rust engine. Installing the v1 Python package
cannot register a v2 adapter. Engine implementation belongs in the
[`alberttwong/dbt` fork](https://github.com/alberttwong/dbt) of
[`dbt-labs/dbt`](https://github.com/dbt-labs/dbt); integration fixtures and tooling
remain in this repository under `v2/`.

See the [v2 development guide](v2/README.md) and
[issue #69](https://github.com/alberttwong/redis-dbt-adapter-with-project/issues/69).
The v2 smoke runner does not use the v1 adapter or change the NYC taxi schemas.
