import pytest

from dbt.tests.adapter.basic.expected_catalog import base_expected_catalog, expected_references_catalog, no_stats
from dbt.tests.adapter.basic.test_adapter_methods import BaseAdapterMethod
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.adapter.basic.test_docs_generate import BaseDocsGenerate, BaseDocsGenReferences
from dbt.tests.adapter.basic.test_empty import BaseEmpty
from dbt.tests.adapter.basic.test_ephemeral import BaseEphemeral
from dbt.tests.adapter.basic.test_generic_tests import BaseGenericTests
from dbt.tests.adapter.basic.test_get_catalog_for_single_relation import BaseGetCatalogForSingleRelation
from dbt.tests.adapter.basic.test_incremental import (
    BaseIncremental,
    BaseIncrementalBadStrategy,
    BaseIncrementalNotSchemaChange,
)
from dbt.tests.adapter.basic.test_singular_tests import BaseSingularTests
from dbt.tests.adapter.basic.test_singular_tests_ephemeral import BaseSingularTestsEphemeral
from dbt.tests.adapter.basic.test_snapshot_check_cols import BaseSnapshotCheckCols
from dbt.tests.adapter.basic.test_snapshot_timestamp import BaseSnapshotTimestamp
from dbt.tests.adapter.basic.test_table_materialization import BaseTableMaterialization
from dbt.tests.adapter.basic.test_validate_connection import BaseValidateConnection


class TestSimpleMaterializations(BaseSimpleMaterializations):
    pass


class TestSingularTests(BaseSingularTests):
    pass


class TestSingularTestsEphemeral(BaseSingularTestsEphemeral):
    pass


class TestEmpty(BaseEmpty):
    pass


class TestEphemeral(BaseEphemeral):
    pass


class TestIncremental(BaseIncremental):
    pass


class TestIncrementalNotSchemaChange(BaseIncrementalNotSchemaChange):
    pass


class TestIncrementalBadStrategy(BaseIncrementalBadStrategy):
    pass


class TestGenericTests(BaseGenericTests):
    pass


class TestSnapshotCheckCols(BaseSnapshotCheckCols):
    pass


class TestSnapshotTimestamp(BaseSnapshotTimestamp):
    pass


class TestAdapterMethod(BaseAdapterMethod):
    pass


class TestValidateConnection(BaseValidateConnection):
    pass


class TestTableMaterialization(BaseTableMaterialization):
    pass


# The catalog's types are the driver's (GetObjects' xdbc_type_name): seeds'
# integers are BIGINT, and a TIMESTAMP has its precision. There's no owner and
# no table statistics.
CATALOG_TYPES = dict(
    role=None,
    id_type="BIGINT",
    text_type="VARCHAR",
    time_type="TIMESTAMP(6)",
    view_type="VIEW",
    table_type="BASE TABLE",
    model_stats=no_stats(),
)


class TestDocsGenerate(BaseDocsGenerate):
    @pytest.fixture(scope="class")
    def expected_catalog(self, project):
        return base_expected_catalog(project, **CATALOG_TYPES)


class TestDocsGenReferences(BaseDocsGenReferences):
    @pytest.fixture(scope="class")
    def expected_catalog(self, project):
        return expected_references_catalog(project, bigint_type="BIGINT", **CATALOG_TYPES)


@pytest.mark.skip(reason="get_catalog_for_single_relation isn't implemented: dbt-core never calls it")
class TestGetCatalogForSingleRelation(BaseGetCatalogForSingleRelation):
    pass
