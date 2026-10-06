"""dbt retry: dbt-tests-adapter has no tests for it."""

import pytest

from dbt.tests.util import run_dbt, write_file

GOOD_SQL = "select 1 as id"
BAD_SQL = "select no_such_column as id"


class TestRetry:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "independent.sql": GOOD_SQL,
            "failing.sql": BAD_SQL,
            "downstream.sql": "select id from {{ ref('failing') }}",
        }

    def test_retry_runs_only_what_failed(self, project):
        results = run_dbt(["run"], expect_pass=False)
        assert {r.node.name: r.status for r in results} == {
            "independent": "success",
            "failing": "error",
            "downstream": "skipped",
        }

        write_file(GOOD_SQL, project.project_root, "models", "failing.sql")
        results = run_dbt(["retry"])
        assert {r.node.name: r.status for r in results} == {"failing": "success", "downstream": "success"}

        # Nothing left to retry.
        assert len(run_dbt(["retry"])) == 0
