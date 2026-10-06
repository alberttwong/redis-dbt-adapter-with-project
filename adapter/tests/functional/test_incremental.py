import pytest

from dbt.tests.adapter.incremental.test_incremental_merge_exclude_columns import BaseMergeExcludeColumns
from dbt.tests.adapter.incremental.test_incremental_microbatch import BaseMicrobatch
from dbt.tests.adapter.incremental.test_incremental_on_schema_change import BaseIncrementalOnSchemaChange
from dbt.tests.adapter.incremental.test_incremental_predicates import BaseIncrementalPredicates
from dbt.tests.adapter.incremental.test_incremental_unique_id import BaseIncrementalUniqueKey


class TestIncrementalUniqueKey(BaseIncrementalUniqueKey):
    pass


class TestIncrementalOnSchemaChange(BaseIncrementalOnSchemaChange):
    pass


class TestIncrementalPredicatesDeleteInsert(BaseIncrementalPredicates):
    pass


class TestPredicatesDeleteInsert(BaseIncrementalPredicates):
    # `predicates` is an alias of `incremental_predicates`.
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {"models": {"+predicates": ["id != 2"], "+incremental_strategy": "delete+insert"}}


class TestIncrementalPredicatesMerge(BaseIncrementalPredicates):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "models": {
                "+incremental_predicates": ["dbt_internal_dest.id != 2"],
                "+incremental_strategy": "merge",
            }
        }


class TestMergeExcludeColumns(BaseMergeExcludeColumns):
    pass


class TestMicrobatch(BaseMicrobatch):
    pass
