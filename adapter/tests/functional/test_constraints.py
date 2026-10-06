import pytest

from dbt.tests.adapter.constraints import fixtures
from dbt.tests.adapter.constraints.test_constraints import (
    BaseConstraintQuotedColumn,
    BaseConstraintsRollback,
    BaseConstraintsRuntimeDdlEnforcement,
    BaseIncrementalConstraintsColumnsEqual,
    BaseIncrementalConstraintsRollback,
    BaseIncrementalConstraintsRuntimeDdlEnforcement,
    BaseIncrementalContractSqlHeader,
    BaseIncrementalForeignKeyConstraint,
    BaseModelConstraintsRuntimeEnforcement,
    BaseTableConstraintsColumnsEqual,
    BaseTableContractSqlHeader,
    BaseViewConstraintsColumnsEqual,
)


# The suite's contracts declare `integer` for columns like `select 1 as id`:
# an integer literal is INTEGER on Postgres and BIGINT on the driver. So here
# they're bigint, and so are the casts the models compare with them.
BIGINT = {"data_type: integer": "data_type: bigint", "dbt.type_int()": "dbt.type_bigint()"}


@pytest.fixture(scope="module", autouse=True)
def bigint_contracts():
    with pytest.MonkeyPatch.context() as mp:
        for name, value in vars(fixtures).items():
            if isinstance(value, str):
                for old, new in BIGINT.items():
                    value = value.replace(old, new)
                mp.setattr(fixtures, name, value)
        yield


class RedisColumnTypes:
    @pytest.fixture
    def string_type(self):
        return "VARCHAR"

    @pytest.fixture
    def int_type(self):
        return "BIGINT"

    @pytest.fixture
    def data_types(self, schema_int_type, int_type, string_type):
        # sql_column_value, schema_data_type, error_data_type. The driver has
        # no arrays, and JSON is text (its JSON functions take strings).
        return [
            ["1", schema_int_type, int_type],
            ["'1'", string_type, string_type],
            ["true", "boolean", "BOOLEAN"],
            ["cast('2013-11-03 00:00:00-07' as timestamp with time zone)", "timestamp with time zone", "TIMESTAMP WITH TIME ZONE"],
            ["cast('2013-11-03 00:00:00-07' as timestamp)", "timestamp", "TIMESTAMP"],
            ["cast('1' as numeric)", "numeric", "NUMERIC"],
        ]


# The suite's expected DDL, with bigint ids (see BIGINT).
COLUMN_CONSTRAINTS_SQL = """
create table <model_identifier> (
    id bigint not null primary key check ((id > 0)) check (id >= 1) references <foreign_key_model_identifier> (id) unique,
    color text,
    date_day text
) ;
insert into <model_identifier> (
    id ,
    color ,
    date_day
)
(
    select
       id,
       color,
       date_day
       from
    (
        -- depends_on: <foreign_key_model_identifier>
        select
            'blue' as color,
            1 as id,
            '2019-01-01' as date_day
    ) as model_subq
);
"""

MODEL_CONSTRAINTS_SQL = """
create table <model_identifier> (
    id bigint not null,
    color text,
    date_day text,
    check ((id > 0)),
    check (id >= 1),
    primary key (id),
    constraint strange_uniqueness_requirement unique (color, date_day),
    foreign key (id) references <foreign_key_model_identifier> (id)
) ;
insert into <model_identifier> (
    id ,
    color ,
    date_day
)
(
    select
       id,
       color,
       date_day
       from
    (
        -- depends_on: <foreign_key_model_identifier>
        select
            'blue' as color,
            1 as id,
            '2019-01-01' as date_day
    ) as model_subq
);
"""

QUOTED_COLUMN_SQL = """
create table <model_identifier> (
    id bigint not null,
    "from" text not null,
    date_day text,
    check (("from" = 'blue'))
) ;
insert into <model_identifier> (
    id, "from", date_day
)
(
    select id, "from", date_day
    from (
        select
          'blue' as "from",
          1 as id,
          '2019-01-01' as date_day
    ) as model_subq
);
"""


class TestTableConstraintsColumnsEqual(RedisColumnTypes, BaseTableConstraintsColumnsEqual):
    pass


class TestViewConstraintsColumnsEqual(RedisColumnTypes, BaseViewConstraintsColumnsEqual):
    pass


class TestIncrementalConstraintsColumnsEqual(RedisColumnTypes, BaseIncrementalConstraintsColumnsEqual):
    pass


class TestConstraintsRuntimeDdlEnforcement(BaseConstraintsRuntimeDdlEnforcement):
    @pytest.fixture(scope="class")
    def expected_sql(self):
        return COLUMN_CONSTRAINTS_SQL


class TestIncrementalConstraintsRuntimeDdlEnforcement(BaseIncrementalConstraintsRuntimeDdlEnforcement):
    @pytest.fixture(scope="class")
    def expected_sql(self):
        return COLUMN_CONSTRAINTS_SQL


class TestModelConstraintsRuntimeEnforcement(BaseModelConstraintsRuntimeEnforcement):
    @pytest.fixture(scope="class")
    def expected_sql(self):
        return MODEL_CONSTRAINTS_SQL


class TestConstraintQuotedColumn(BaseConstraintQuotedColumn):
    @pytest.fixture(scope="class")
    def expected_sql(self):
        return QUOTED_COLUMN_SQL


class RedisNotNullError:
    @pytest.fixture(scope="class")
    def expected_error_messages(self):
        return ['NULL value in column "id" violates not-null constraint']


class TestConstraintsRollback(RedisNotNullError, BaseConstraintsRollback):
    pass


class TestIncrementalConstraintsRollback(RedisNotNullError, BaseIncrementalConstraintsRollback):
    pass


# Postgres's current_setting('timezone') isn't in the driver; the session time
# zone the header sets shows in current_timestamp's text instead.
SQL_HEADER_MODEL = """
{{{{ config(materialized="{materialized}", on_schema_change="append_new_columns") }}}}

{{% call set_sql_header(config) %}}
set session time zone 'Asia/Kolkata';
{{%- endcall %}}
select cast(current_timestamp as varchar) as column_name
"""


class TestTableContractSqlHeader(BaseTableContractSqlHeader):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_contract_sql_header.sql": SQL_HEADER_MODEL.format(materialized="table"),
            "constraints_schema.yml": fixtures.model_contract_header_schema_yml,
        }


class TestIncrementalContractSqlHeader(BaseIncrementalContractSqlHeader):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_contract_sql_header.sql": SQL_HEADER_MODEL.format(materialized="incremental"),
            "constraints_schema.yml": fixtures.model_contract_header_schema_yml,
        }


class TestIncrementalForeignKeyConstraint(BaseIncrementalForeignKeyConstraint):
    pass
