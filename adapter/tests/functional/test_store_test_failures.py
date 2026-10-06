from dbt.tests.adapter.store_test_failures_tests.basic import (
    StoreTestFailuresAsExceptions,
    StoreTestFailuresAsGeneric,
    StoreTestFailuresAsInteractions,
    StoreTestFailuresAsProjectLevelEphemeral,
    StoreTestFailuresAsProjectLevelOff,
    StoreTestFailuresAsProjectLevelView,
)
from dbt.tests.adapter.store_test_failures_tests.test_store_test_failures import (
    BaseStoreTestFailures,
    BaseStoreTestFailuresLimit,
)


class TestStoreTestFailures(BaseStoreTestFailures):
    pass


class TestStoreTestFailuresLimit(BaseStoreTestFailuresLimit):
    pass


class TestStoreTestFailuresAsInteractions(StoreTestFailuresAsInteractions):
    pass


class TestStoreTestFailuresAsProjectLevelOff(StoreTestFailuresAsProjectLevelOff):
    pass


class TestStoreTestFailuresAsProjectLevelView(StoreTestFailuresAsProjectLevelView):
    pass


class TestStoreTestFailuresAsProjectLevelEphemeral(StoreTestFailuresAsProjectLevelEphemeral):
    pass


class TestStoreTestFailuresAsGeneric(StoreTestFailuresAsGeneric):
    pass


class TestStoreTestFailuresAsExceptions(StoreTestFailuresAsExceptions):
    pass
