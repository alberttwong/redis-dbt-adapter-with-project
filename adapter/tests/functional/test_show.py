from dbt.tests.adapter.dbt_show.test_dbt_show import BaseShowLimit, BaseShowSqlHeader


class TestShowLimit(BaseShowLimit):
    pass


class TestShowSqlHeader(BaseShowSqlHeader):
    pass


# Not BaseShowDoesNotHandleDoubleLimit: the adapter's get_limit_sql wraps the
# query in a subquery, so `dbt show --limit` of a query with its own LIMIT
# works, and there's no error to check for.
