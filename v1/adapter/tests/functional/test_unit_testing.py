from dbt.tests.adapter.unit_testing.test_case_insensitivity import BaseUnitTestCaseInsensivity
from dbt.tests.adapter.unit_testing.test_invalid_input import BaseUnitTestInvalidInput
from dbt.tests.adapter.unit_testing.test_quoted_reserved_word_column_names import (
    BaseUnitTestQuotedReservedWordColumnNames,
)
from dbt.tests.adapter.unit_testing.test_types import (
    BaseUnitTestingTypes,
    BaseUnitTestingVarcharFixtureNoTruncation,
)


class TestUnitTestCaseInsensitivity(BaseUnitTestCaseInsensivity):
    pass


class TestUnitTestInvalidInput(BaseUnitTestInvalidInput):
    pass


class TestUnitTestQuotedReservedWordColumnNames(BaseUnitTestQuotedReservedWordColumnNames):
    pass


class TestUnitTestingTypes(BaseUnitTestingTypes):
    pass


class TestUnitTestingVarcharFixtureNoTruncation(BaseUnitTestingVarcharFixtureNoTruncation):
    pass
