import os
import re

from dbt.tests.adapter.ephemeral.test_ephemeral import (
    BaseEphemeralErrorHandling,
    BaseEphemeralMulti,
    BaseEphemeralNested,
)
from dbt.tests.util import check_relations_equal, run_dbt


def compiled_sql(path):
    """The SQL dbt ran, without digits (the test schema's) or whitespace,
    as the suite compares it."""
    assert os.path.exists(path)
    with open(path) as fp:
        return "".join(re.sub(r"\d+", "", fp.read()).split())


# The suite's tests, with relations rendered as the adapter renders them:
# schema.table, unquoted (Postgres's are "database"."schema"."table").


class TestEphemeralMulti(BaseEphemeralMulti):
    def test_ephemeral_multi(self, project):
        run_dbt(["seed"])
        results = run_dbt(["run"])
        assert len(results) == 3

        check_relations_equal(project.adapter, ["seed", "dependent"])
        check_relations_equal(project.adapter, ["seed", "double_dependent"])
        check_relations_equal(project.adapter, ["seed", "super_dependent"])
        expected_sql = (
            "create view test_test_ephemeral.double_dependent__dbt_tmp as ("
            "with __dbt__cte__base as ("
            "select * from test_test_ephemeral.seed"
            "),  __dbt__cte__base_copy as ("
            "select * from __dbt__cte__base"
            ")-- base_copy just pulls from base. Make sure the listed"
            "-- graph of CTEs all share the same dbt_cte__base cte"
            "select * from __dbt__cte__base where gender = 'Male'"
            "union all"
            "select * from __dbt__cte__base_copy where gender = 'Female'"
            ");"
        )
        assert compiled_sql("./target/run/test/models/double_dependent.sql") == "".join(expected_sql.split())


class TestEphemeralNested(BaseEphemeralNested):
    def test_ephemeral_nested(self, project):
        results = run_dbt(["run"])
        assert len(results) == 2
        expected_sql = (
            "create view test_test_ephemeral.root_view__dbt_tmp as ("
            "with __dbt__cte__ephemeral_level_two as ("
            "select * from test_test_ephemeral.source_table"
            "),  __dbt__cte__ephemeral as ("
            "select * from __dbt__cte__ephemeral_level_two"
            ")select * from __dbt__cte__ephemeral"
            ");"
        )
        assert compiled_sql("./target/run/test/models/root_view.sql") == "".join(expected_sql.split())


class TestEphemeralErrorHandling(BaseEphemeralErrorHandling):
    pass
