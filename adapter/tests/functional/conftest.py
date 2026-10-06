"""Fixtures for dbt's adapter test suite (dbt-tests-adapter).

    uv run pytest -n 4

Each test class gets its own schema, which the suite drops afterwards. Point
REDIS_URI at a Redis you don't mind tests writing to (redis://localhost:6380/0
by default, as in profiles.yml); REDIS_USERNAME, REDIS_PASSWORD and
REDIS_ADBC_DRIVER work as for the project.
"""

import os
from pathlib import Path

import pytest

from dbt.tests.util import get_connection

pytest_plugins = ["dbt.tests.fixtures.project"]

# `make driver` puts it here. The suite runs each test from a temporary
# directory, so the path must be absolute.
DRIVER = Path(__file__).resolve().parents[3] / "driver" / "libadbc_driver_redis"

# Tests that fail on a driver issue. They're strict xfails: once a driver
# release fixes the issue they pass, and the run fails until they're removed
# here.
UNION_TYPES = "UNION's column types (driver #187: https://github.com/alberttwong/redis-adbc-driver/issues/187)"
DATE_FUNCTION = "no date(x) (driver #188: https://github.com/alberttwong/redis-adbc-driver/issues/188)"
DRIVER_ISSUES = {
    # Expected rows: cast('2022-02-14' as date) union all select '2020-02-12'.
    "test_incremental.py::TestIncrementalUniqueKey::test__one_unique_key": UNION_TYPES,
    "test_incremental.py::TestIncrementalUniqueKey::test__unary_unique_key_list": UNION_TYPES,
    "test_incremental.py::TestIncrementalUniqueKey::test__duplicated_unary_unique_key_list": UNION_TYPES,
    "test_incremental.py::TestIncrementalUniqueKey::test__trinary_unique_key_list": UNION_TYPES,
    # A DATE updated_at with invalidate_hard_deletes.
    "test_snapshot.py::TestSimpleSnapshot": UNION_TYPES,
    # dbt_valid_to_current: "date('2099-12-31')".
    "test_snapshot.py::TestSnapshotDbtValidToCurrent": DATE_FUNCTION,
    "test_snapshot.py::TestSnapshotNewRecordDbtValidToCurrent": DATE_FUNCTION,
}


def pytest_collection_modifyitems(items):
    for item in items:
        for test, reason in DRIVER_ISSUES.items():
            if f"/{test}::" in f"/{item.nodeid}::":
                item.add_marker(pytest.mark.xfail(reason=reason, strict=True))


@pytest.fixture(scope="class")
def dbt_profile_target():
    return {
        "type": "redis_adbc",
        "driver": os.environ.get("REDIS_ADBC_DRIVER") or str(DRIVER),
        "uri": os.environ.get("REDIS_URI", "redis://localhost:6380/0"),
        "username": os.environ.get("REDIS_USERNAME", ""),
        "password": os.environ.get("REDIS_PASSWORD", ""),
        "threads": 4,
    }


@pytest.fixture(scope="class")
def profile_user():
    # The suite's default reads the Postgres profile's `user`; the docs
    # catalog has no owner here.
    return None


@pytest.fixture(scope="class", autouse=True)
def drop_extra_schemas(project):
    """Drop the schemas dbt made for a test besides its own (…_seeds,
    …_dbt_test__audit, …): the suite drops only the ones it created, and
    the rest would stay in Redis. The suite's teardown, which runs after
    this, drops them."""
    yield
    with get_connection(project.adapter):
        schemas = project.adapter.list_schemas(project.database)
    project.created_schemas.extend(
        s for s in schemas if s.startswith(project.test_schema) and s not in project.created_schemas
    )
