import pytest

from dbt.tests.adapter.dbt_clone.test_dbt_clone import (
    BaseClonePossible,
    BaseCloneNotPossible,
    BaseCloneSameSourceAndTarget,
    BaseCloneSameTargetAndState,
)


# Redis has no zero-copy clone, so dbt clone creates views of the deferred
# relations (the "not possible" path).
@pytest.mark.skip(reason="Redis has no zero-copy table clone; dbt clone creates views (TestCloneNotPossible)")
class TestClonePossible(BaseClonePossible):
    pass


class TestCloneNotPossible(BaseCloneNotPossible):
    pass


@pytest.mark.skip(reason="Redis has no zero-copy table clone; dbt logs the skip only on that path")
class TestCloneSameSourceAndTarget(BaseCloneSameSourceAndTarget):
    pass


class TestCloneSameTargetAndState(BaseCloneSameTargetAndState):
    pass
