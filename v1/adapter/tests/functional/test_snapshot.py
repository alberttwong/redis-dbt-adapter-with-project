from dbt.tests.adapter.simple_snapshot.new_record_check_mode import BaseSnapshotNewRecordCheckMode
from dbt.tests.adapter.simple_snapshot.new_record_dbt_valid_to_current import BaseSnapshotNewRecordDbtValidToCurrent
from dbt.tests.adapter.simple_snapshot.new_record_timestamp_mode import BaseSnapshotNewRecordTimestampMode
from dbt.tests.adapter.simple_snapshot.test_ephemeral_snapshot_hard_deletes import (
    BaseSnapshotEphemeralHardDeletes,
    BaseSnapshotNewColumnSpecificCheckCols,
    BaseSnapshotNewColumnTimestampStrategy,
    BaseSnapshotNewColumnWithDeletes,
)
from dbt.tests.adapter.simple_snapshot.test_snapshot import BaseSimpleSnapshot, BaseSnapshotCheck
from dbt.tests.adapter.simple_snapshot.test_various_configs import (
    BaseSnapshotColumnNames,
    BaseSnapshotColumnNamesFromDbtProject,
    BaseSnapshotDbtValidToCurrent,
    BaseSnapshotInvalidColumnNames,
    BaseSnapshotMultiUniqueKey,
)


class TestSimpleSnapshot(BaseSimpleSnapshot):
    pass


class TestSnapshotCheck(BaseSnapshotCheck):
    pass


class TestSnapshotColumnNames(BaseSnapshotColumnNames):
    pass


class TestSnapshotColumnNamesFromDbtProject(BaseSnapshotColumnNamesFromDbtProject):
    pass


class TestSnapshotInvalidColumnNames(BaseSnapshotInvalidColumnNames):
    pass


class TestSnapshotDbtValidToCurrent(BaseSnapshotDbtValidToCurrent):
    pass


class TestSnapshotMultiUniqueKey(BaseSnapshotMultiUniqueKey):
    pass


class TestSnapshotNewRecordTimestampMode(BaseSnapshotNewRecordTimestampMode):
    pass


class TestSnapshotNewRecordCheckMode(BaseSnapshotNewRecordCheckMode):
    pass


class TestSnapshotNewRecordDbtValidToCurrent(BaseSnapshotNewRecordDbtValidToCurrent):
    pass


class TestSnapshotEphemeralHardDeletes(BaseSnapshotEphemeralHardDeletes):
    pass


class TestSnapshotNewColumnTimestampStrategy(BaseSnapshotNewColumnTimestampStrategy):
    pass


class TestSnapshotNewColumnSpecificCheckCols(BaseSnapshotNewColumnSpecificCheckCols):
    pass


class TestSnapshotNewColumnWithDeletes(BaseSnapshotNewColumnWithDeletes):
    pass
