"""Python models: dbt's suite, and the adapter's own cases."""

import pytest

from dbt.tests.adapter.python_model import test_python_model as suite
from dbt.tests.adapter.python_model.test_python_model import (
    BasePythonEmptyTests,
    BasePythonIncrementalTests,
    BasePythonMetaGetTests,
    BasePythonModelTests,
    BasePythonSampleTests,
)
from dbt.tests.util import get_connection, relation_from_name, run_dbt, run_dbt_and_capture, write_file

# The suite's models use a Spark-like DataFrame API; refs here are pyarrow
# Tables, so these are its models in pyarrow.


class TestPythonModel(BasePythonModelTests):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "schema.yml": suite.schema_yml,
            "my_sql_model.sql": suite.basic_sql,
            "my_versioned_sql_model_v1.sql": suite.basic_sql,
            "my_python_model.py": suite.basic_python.replace("df.limit(2)", "df.slice(0, 2)"),
            "second_sql_model.sql": suite.second_sql,
        }


@pytest.mark.skip(reason="Python models are tables only: dbt's incremental materialization runs SQL models only")
class TestPythonIncremental(BasePythonIncrementalTests):
    pass


META_GET_PY = """
import pyarrow as pa

def model(dbt, session):
    dbt.config(
        materialized='table',
        meta={
            'owner': 'data-team',
            'priority': 'high',
            'version': 2
        }
    )
    owner = dbt.config.meta_get('owner')
    priority = dbt.config.meta_get('priority', 'low')
    version = dbt.config.meta_get('version')
    missing = dbt.config.meta_get('nonexistent', 'default-value')
    return pa.table({'id': [1], 'owner': [owner], 'priority': [priority], 'version': [str(version)], 'missing': [missing]})
"""

META_FROM_SCHEMA_PY = """
import pyarrow as pa

def model(dbt, session):
    owner = dbt.config.meta_get('owner')
    environment = dbt.config.meta_get('environment', 'dev')
    return pa.table({'id': [1], 'owner': [owner], 'environment': [environment]})
"""


class TestPythonMetaGet(BasePythonMetaGetTests):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "meta_test.py": META_GET_PY,
            "meta_from_schema.py": META_FROM_SCHEMA_PY,
            "schema.yml": suite.schema_yml_with_meta,
        }


class TestPythonEmpty(BasePythonEmptyTests):
    pass


class TestPythonSample(BasePythonSampleTests):
    pass


SEED_CSV = """id,name
1,a
2,b
3,c
"""

RESULT_MODELS = {
    "from_pandas.py": """
import pandas as pd

def model(dbt, session):
    df = dbt.ref("seed").to_pandas().set_index("id")
    return df.reset_index().assign(doubled=lambda d: d["id"] * 2)
""",
    "from_polars.py": """
import polars as pl

def model(dbt, session):
    return pl.from_arrow(dbt.ref("seed")).lazy().with_columns((pl.col("id") * 2).alias("doubled"))
""",
    "from_reader.py": """
import pyarrow as pa

def model(dbt, session):
    return pa.RecordBatchReader.from_batches(dbt.ref("seed").schema, dbt.ref("seed").to_batches())
""",
    "empty.py": """
import pyarrow as pa

def model(dbt, session):
    return dbt.ref("seed").slice(0, 0)
""",
    "with_session.py": """
import pyarrow as pa

def model(dbt, session):
    dbt.config(materialized="table")
    with session.cursor() as cur:
        cur.execute(f"select count(*) from {dbt.this.schema}.seed")
        seed_rows = cur.fetchone()[0]
    materialized = dbt.config.get("materialized")
    return pa.table({
        "this": [str(dbt.this)],
        "identifier": [dbt.this.identifier],
        "materialized": [materialized],
        "is_incremental": [dbt.is_incremental],
        "seed_rows": [seed_rows],
    })
""",
}


class TestPythonModelResults:
    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": SEED_CSV}

    @pytest.fixture(scope="class")
    def models(self):
        return RESULT_MODELS

    def rows(self, project, name, columns="*"):
        relation = relation_from_name(project.adapter, name)
        return project.run_sql(f"select {columns} from {relation} order by 1", fetch="all")

    def test_results(self, project):
        run_dbt(["seed"])
        results = run_dbt(["run"])
        assert len(results) == len(RESULT_MODELS)

        doubled = [(1, "a", 2), (2, "b", 4), (3, "c", 6)]
        assert [tuple(r) for r in self.rows(project, "from_pandas", "id, name, doubled")] == doubled
        assert [tuple(r) for r in self.rows(project, "from_polars", "id, name, doubled")] == doubled
        assert [tuple(r) for r in self.rows(project, "from_reader")] == [(1, "a"), (2, "b"), (3, "c")]
        assert self.rows(project, "empty") == []
        with get_connection(project.adapter):
            columns = project.adapter.get_columns_in_relation(relation_from_name(project.adapter, "empty"))
        assert [c.name for c in columns] == ["id", "name"]
        [row] = self.rows(project, "with_session")
        assert tuple(row) == (f"{project.test_schema}.with_session", "with_session", "table", False, 3)

        # A rebuild replaces the table (dbt's rename swap).
        write_file(RESULT_MODELS["empty.py"].replace("slice(0, 0)", "slice(0, 1)"), project.project_root, "models", "empty.py")
        run_dbt(["run", "-s", "empty"])
        assert [tuple(r) for r in self.rows(project, "empty")] == [(1, "a")]


class TestPythonModelErrors:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "bad_result.py": "def model(dbt, session):\n    return 42\n",
            "raises.py": "def model(dbt, session):\n    df = int('no good')\n    return df\n",
            "bad_sql.py": "def model(dbt, session):\n    session.cursor().execute('select * from no_such_table_here')\n    return None\n",
            "incremental.py": "def model(dbt, session):\n    dbt.config(materialized='incremental')\n    return None\n",
        }

    def test_errors(self, project):
        results, output = run_dbt_and_capture(["run"], expect_pass=False)
        messages = {r.node.name: r.message for r in results}
        assert "model() returned a builtins.int" in messages["bad_result"]
        # The model's traceback, with its file and line.
        assert "Python model failed" in messages["raises"]
        assert 'models/raises.py", line 2, in model' in messages["raises"]
        assert "ValueError: invalid literal for int() with base 10: 'no good'" in messages["raises"]
        assert "no_such_table_here" in messages["bad_sql"]
        assert "Database Error in model bad_sql" in output
        assert "only supports languages ['sql']" in messages["incremental"]
