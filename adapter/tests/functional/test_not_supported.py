"""The suite's tests for what Redis doesn't have, skipped with the reason."""

import pytest

from dbt.tests.adapter.grants.test_incremental_grants import BaseIncrementalGrants
from dbt.tests.adapter.grants.test_invalid_grants import BaseInvalidGrants
from dbt.tests.adapter.grants.test_model_grants import BaseModelGrants
from dbt.tests.adapter.grants.test_seed_grants import BaseSeedGrants
from dbt.tests.adapter.grants.test_snapshot_grants import BaseSnapshotGrants
from dbt.tests.adapter.materialized_view.basic import MaterializedViewBasic
from dbt.tests.adapter.materialized_view.changes import MaterializedViewChanges
from dbt.tests.adapter.python_model.test_python_model import (
    BasePythonEmptyTests,
    BasePythonIncrementalTests,
    BasePythonMetaGetTests,
    BasePythonModelTests,
    BasePythonSampleTests,
)

NO_GRANTS = pytest.mark.skip(reason="Redis controls access with ACLs, not GRANT; the adapter skips grants with a warning")
NO_MATERIALIZED_VIEWS = pytest.mark.skip(reason="Redis has no materialized views")
NO_PYTHON_MODELS = pytest.mark.skip(reason="Python models aren't supported yet (#52)")


@NO_GRANTS
class TestModelGrants(BaseModelGrants):
    pass


@NO_GRANTS
class TestIncrementalGrants(BaseIncrementalGrants):
    pass


@NO_GRANTS
class TestSeedGrants(BaseSeedGrants):
    pass


@NO_GRANTS
class TestSnapshotGrants(BaseSnapshotGrants):
    pass


@NO_GRANTS
class TestInvalidGrants(BaseInvalidGrants):
    pass


@NO_MATERIALIZED_VIEWS
class TestMaterializedViewBasic(MaterializedViewBasic):
    pass


@NO_MATERIALIZED_VIEWS
class TestMaterializedViewChanges(MaterializedViewChanges):
    pass


@NO_PYTHON_MODELS
class TestPythonModel(BasePythonModelTests):
    pass


@NO_PYTHON_MODELS
class TestPythonIncremental(BasePythonIncrementalTests):
    pass


@NO_PYTHON_MODELS
class TestPythonMetaGet(BasePythonMetaGetTests):
    pass


@NO_PYTHON_MODELS
class TestPythonEmpty(BasePythonEmptyTests):
    pass


@NO_PYTHON_MODELS
class TestPythonSample(BasePythonSampleTests):
    pass
