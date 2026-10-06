from pathlib import Path

import pytest

from dbt.tests.adapter.hooks import fixtures
from dbt.tests.adapter.hooks.test_model_hooks import (
    MODEL_POST_HOOK,
    MODEL_PRE_HOOK,
    BaseDuplicateHooksInConfigs,
    BaseHookRefs,
    BaseHooksRefsOnSeeds,
    BasePrePostModelHooks,
    BasePrePostModelHooksInConfig,
    BasePrePostModelHooksInConfigKwargs,
    BasePrePostModelHooksInConfigWithCount,
    BasePrePostModelHooksOnSeeds,
    BasePrePostModelHooksOnSeedsPlusPrefixed,
    BasePrePostModelHooksOnSeedsPlusPrefixedWhitespace,
    BasePrePostModelHooksOnSnapshots,
    BasePrePostSnapshotHooksInConfigKwargs,
)
from dbt.tests.adapter.hooks.test_run_hooks import BaseAfterRunHooks, BasePrePostRunHooks


@pytest.fixture(scope="module")
def test_data_dir():
    # The suite's on_model_hook / on_run_hook tables (portable SQL).
    return Path(fixtures.__file__).parent / "data"


def check_target(ctx, project):
    """The hooks record `target`'s fields; these are a redis_adbc target's
    (it has no dbname, host or user)."""
    assert ctx["target_dbname"] == ""
    assert ctx["target_host"] == ""
    assert ctx["target_name"] == "default"
    assert ctx["target_schema"] == project.test_schema
    assert ctx["target_threads"] == 4
    assert ctx["target_type"] == "redis_adbc"
    assert ctx["target_user"] == ""
    assert ctx["target_pass"] == ""
    assert ctx["run_started_at"], "run_started_at was not set"
    assert ctx["invocation_id"], "invocation_id was not set"


class RedisModelHooks:
    def check_hooks(self, state, project, host, count=1):
        for ctx in self.get_ctx_vars(state, count=count, project=project):
            assert ctx["test_state"] == state
            check_target(ctx, project)
            assert ctx["thread_id"].startswith("Thread-")


# Postgres's `vacuum` hooks, outside the transaction, as a query instead.
HOOKS_OUTSIDE_TRANSACTION = {
    "models": {
        "test": {
            "pre-hook": [
                MODEL_PRE_HOOK,
                {"sql": "select count(*) from {{ this.schema }}.on_model_hook", "transaction": False},
            ],
            "post-hook": [
                {"sql": "select count(*) from {{ this.schema }}.on_model_hook", "transaction": False},
                MODEL_POST_HOOK,
            ],
        }
    }
}


class TestPrePostModelHooks(RedisModelHooks, BasePrePostModelHooks):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return HOOKS_OUTSIDE_TRANSACTION


class TestHookRefs(RedisModelHooks, BaseHookRefs):
    pass


class TestPrePostModelHooksOnSeeds(BasePrePostModelHooksOnSeeds):
    pass


class TestHooksRefsOnSeeds(BaseHooksRefsOnSeeds):
    pass


class TestPrePostModelHooksOnSeedsPlusPrefixed(BasePrePostModelHooksOnSeedsPlusPrefixed):
    pass


class TestPrePostModelHooksOnSeedsPlusPrefixedWhitespace(BasePrePostModelHooksOnSeedsPlusPrefixedWhitespace):
    pass


class TestPrePostModelHooksOnSnapshots(BasePrePostModelHooksOnSnapshots):
    pass


class TestPrePostModelHooksInConfig(RedisModelHooks, BasePrePostModelHooksInConfig):
    pass


class TestPrePostModelHooksInConfigWithCount(RedisModelHooks, BasePrePostModelHooksInConfigWithCount):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return HOOKS_OUTSIDE_TRANSACTION


class TestPrePostModelHooksInConfigKwargs(RedisModelHooks, BasePrePostModelHooksInConfigKwargs):
    pass


class TestPrePostSnapshotHooksInConfigKwargs(BasePrePostSnapshotHooksInConfigKwargs):
    pass


class TestDuplicateHooksInConfigs(BaseDuplicateHooksInConfigs):
    pass


class TestPrePostRunHooks(BasePrePostRunHooks):
    def check_hooks(self, state, project, host):
        ctx = self.get_ctx_vars(state, project)
        assert ctx["test_state"] == state
        check_target(ctx, project)
        assert ctx["thread_id"].startswith("Thread-") or ctx["thread_id"] == "MainThread"


class TestAfterRunHooks(BaseAfterRunHooks):
    pass
