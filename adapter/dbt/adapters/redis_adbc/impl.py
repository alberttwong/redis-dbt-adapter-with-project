"""dbt adapter for Redis via the Redis ADBC driver.

The driver speaks enough SQL for dbt's generated statements (CTAS, CTEs,
subqueries, joins, set operations, views, ALTER TABLE ... RENAME). Metadata
comes from ADBC GetObjects; the include/ macros cover the remaining gaps (no
transactions, TRUNCATE, temporary tables, or view renames).
"""

import datetime
import decimal
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import agate
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
from dbt_common.clients.agate_helper import table_from_rows
from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.base import BaseRelation, available
from dbt.adapters.base.column import Column
from dbt.adapters.base.relation import AdapterTrackingRelationInfo, InformationSchema
from dbt.adapters.contracts.relation import Policy, RelationType
from dbt.adapters.redis_adbc.connections import RedisAdbcConnectionManager
from dbt.adapters.sql import SQLAdapter


def arrow_type_to_sql(t) -> str:
    if not isinstance(t, pa.DataType):
        return str(t)
    if pa.types.is_boolean(t):
        return "BOOLEAN"
    if pa.types.is_int8(t) or pa.types.is_int16(t) or pa.types.is_uint8(t):
        return "SMALLINT"
    if pa.types.is_int32(t) or pa.types.is_uint16(t):
        return "INTEGER"
    if pa.types.is_integer(t):
        return "BIGINT"
    if pa.types.is_float16(t) or pa.types.is_float32(t):
        return "REAL"
    if pa.types.is_floating(t):
        return "DOUBLE PRECISION"
    if pa.types.is_decimal(t):
        return f"NUMERIC({t.precision},{t.scale})"
    if pa.types.is_string(t) or pa.types.is_large_string(t) or pa.types.is_string_view(t):
        return "VARCHAR"
    if pa.types.is_binary(t) or pa.types.is_large_binary(t) or pa.types.is_fixed_size_binary(t):
        return "VARBINARY"
    if pa.types.is_date(t):
        return "DATE"
    if pa.types.is_time(t):
        return "TIME"
    if pa.types.is_timestamp(t):
        return "TIMESTAMP WITH TIME ZONE" if t.tz else "TIMESTAMP"
    return str(t).upper()


# SQL type names accepted in load_csv_file(column_types=...) -> Arrow types.
_SQL_TO_ARROW = {
    "BOOLEAN": pa.bool_(),
    "SMALLINT": pa.int16(),
    "INTEGER": pa.int32(),
    "INT": pa.int32(),
    "BIGINT": pa.int64(),
    "REAL": pa.float32(),
    "DOUBLE": pa.float64(),
    "DOUBLE PRECISION": pa.float64(),
    "VARCHAR": pa.string(),
    "TEXT": pa.string(),
    "DATE": pa.date32(),
    "TIME": pa.time64("us"),
    "TIMESTAMP": pa.timestamp("us"),
    "TIMESTAMP WITH TIME ZONE": pa.timestamp("us", tz="UTC"),
    "VARBINARY": pa.binary(),
}


def _sql_to_arrow(sql_type: str) -> pa.DataType:
    key = " ".join(sql_type.upper().split())
    if key.startswith("NUMERIC") or key.startswith("DECIMAL"):
        p, s = key[key.index("(") + 1 : key.index(")")].split(",")
        return pa.decimal128(int(p), int(s))
    if key not in _SQL_TO_ARROW:
        raise DbtRuntimeError(f"Unsupported column type for CSV load: {sql_type}")
    return _SQL_TO_ARROW[key]


@dataclass(frozen=True, eq=False, repr=False)
class RedisAdbcRelation(BaseRelation):
    # Render `schema.table`: the driver has a single catalog ("redis").
    include_policy: Policy = field(default_factory=lambda: Policy(database=False, schema=True, identifier=True))
    quote_policy: Policy = field(default_factory=lambda: Policy(database=False, schema=False, identifier=False))
    # ALTER TABLE ... RENAME works on tables only; views use CREATE OR REPLACE.
    renameable_relations: FrozenSet = frozenset({RelationType.Table})
    replaceable_relations: FrozenSet = frozenset({RelationType.View})


class RedisAdbcAdapter(SQLAdapter):
    ConnectionManager = RedisAdbcConnectionManager
    Relation = RedisAdbcRelation
    Column = Column

    @classmethod
    def get_adapter_run_info(cls, config) -> AdapterTrackingRelationInfo:
        # The base class derives the module name from the class name
        # ("redisadbc"); this package lives at dbt.adapters.redis_adbc.
        from dbt.adapters.__about__ import version as base_version
        from dbt.adapters.redis_adbc.__version__ import version

        return AdapterTrackingRelationInfo(
            adapter_name="redis_adbc",
            base_adapter_version=base_version,
            adapter_version=version,
            model_adapter_details={},
        )

    @classmethod
    def date_function(cls) -> str:
        return "current_timestamp"

    @classmethod
    def is_cancelable(cls) -> bool:
        return False

    # --- type conversion for seeds -------------------------------------------------

    @classmethod
    def convert_text_type(cls, agate_table, col_idx):
        return "VARCHAR"

    @classmethod
    def convert_number_type(cls, agate_table, col_idx):
        decimals = agate_table.aggregate(agate.MaxPrecision(col_idx))
        return "DOUBLE PRECISION" if decimals else "BIGINT"

    @classmethod
    def convert_integer_type(cls, agate_table, col_idx):
        return "BIGINT"

    @classmethod
    def convert_boolean_type(cls, agate_table, col_idx):
        return "BOOLEAN"

    @classmethod
    def convert_datetime_type(cls, agate_table, col_idx):
        return "TIMESTAMP"

    @classmethod
    def convert_date_type(cls, agate_table, col_idx):
        return "DATE"

    @classmethod
    def convert_time_type(cls, agate_table, col_idx):
        return "TIME"

    # --- metadata via ADBC GetObjects ---------------------------------------------

    def _adbc(self):
        return self.connections.get_thread_connection().handle.conn

    def _get_objects(self, depth: str, schema: Optional[str] = None, table: Optional[str] = None) -> List[dict]:
        with self.connections.exception_handler("GetObjects"):
            reader = self._adbc().adbc_get_objects(
                depth=depth, db_schema_filter=schema, table_name_filter=table
            )
            return reader.read_all().to_pylist()

    def list_schemas(self, database: str) -> List[str]:
        return [
            s["db_schema_name"]
            for cat in self._get_objects("db_schemas")
            for s in cat["catalog_db_schemas"] or []
        ]

    def check_schema_exists(self, database: str, schema: str) -> bool:
        return schema.casefold() in (s.casefold() for s in self.list_schemas(database))

    def list_relations_without_caching(self, schema_relation: BaseRelation) -> List[BaseRelation]:
        relations = []
        for cat in self._get_objects("tables", schema=schema_relation.schema):
            for s in cat["catalog_db_schemas"] or []:
                if s["db_schema_name"] != schema_relation.schema:
                    continue
                for t in s["db_schema_tables"] or []:
                    relations.append(
                        self.Relation.create(
                            database=cat["catalog_name"],
                            schema=s["db_schema_name"],
                            identifier=t["table_name"],
                            type=RelationType.View if t["table_type"] == "VIEW" else RelationType.Table,
                        )
                    )
        return relations

    def _table_columns(self, schema: str, table: str) -> List[dict]:
        for cat in self._get_objects("columns", schema=schema, table=table):
            for s in cat["catalog_db_schemas"] or []:
                if s["db_schema_name"] != schema:
                    continue
                for t in s["db_schema_tables"] or []:
                    if t["table_name"] == table:
                        return sorted(t["table_columns"] or [], key=lambda c: c["ordinal_position"])
        return []

    def get_columns_in_relation(self, relation: BaseRelation) -> List[Column]:
        return [
            self.Column(column=c["column_name"], dtype=c["xdbc_type_name"])
            for c in self._table_columns(relation.schema, relation.identifier)
        ]

    def drop_schema(self, relation: BaseRelation) -> None:
        # DROP SCHEMA fails unless the schema is empty.
        for rel in self.list_relations_without_caching(relation):
            self.drop_relation(rel)
        super().drop_schema(relation)

    def _get_one_catalog(
        self,
        information_schema: InformationSchema,
        schemas: Set[str],
        used_schemas: FrozenSet[Tuple[str, str]],
    ) -> agate.Table:
        rows = []
        for schema in schemas:
            for cat in self._get_objects("columns", schema=schema):
                for s in cat["catalog_db_schemas"] or []:
                    for t in s["db_schema_tables"] or []:
                        for c in t["table_columns"] or []:
                            rows.append(
                                [
                                    cat["catalog_name"],
                                    s["db_schema_name"],
                                    t["table_name"],
                                    "VIEW" if t["table_type"] == "VIEW" else "BASE TABLE",
                                    None,
                                    c["column_name"],
                                    c["ordinal_position"],
                                    c["xdbc_type_name"],
                                    c["remarks"],
                                    None,
                                ]
                            )
        columns = [
            "table_database",
            "table_schema",
            "table_name",
            "table_type",
            "table_comment",
            "column_name",
            "column_index",
            "column_type",
            "column_comment",
            "table_owner",
        ]
        return self._catalog_filter_table(table_from_rows(rows, columns), used_schemas)

    # --- bulk loading through ADBC ingest -----------------------------------------

    def _ingest(self, relation: BaseRelation, table: pa.Table, mode: str) -> int:
        with self.connections.exception_handler(f"ingest into {relation}"):
            cur = self.connections.get_thread_connection().handle.cursor()
            try:
                return cur.adbc_ingest(relation.identifier, table, mode=mode, db_schema_name=relation.schema)
            finally:
                cur.close()

    @available
    def load_csv_file(
        self,
        relation: BaseRelation,
        path: str,
        column_types: Dict[str, str],
        limit: Optional[int] = None,
        sample_every: int = 1,
        row_number_column: Optional[str] = None,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S",
    ) -> int:
        """Replace `relation` with the rows of a (optionally gzipped) CSV file.

        Streams the file with pyarrow, keeps every `sample_every`-th row up to
        `limit` rows, and writes them with ADBC bulk ingest. `column_types`
        maps CSV column -> SQL type. If `row_number_column` is set, it is
        prepended as a BIGINT holding each row's 1-based position in the file,
        which stays the same however the file is sampled or reloaded.
        """
        schema = {name: _sql_to_arrow(t) for name, t in column_types.items()}
        reader = pacsv.open_csv(
            path,
            convert_options=pacsv.ConvertOptions(
                column_types=schema,
                include_columns=list(schema),
                timestamp_parsers=[timestamp_format],
                strings_can_be_null=True,
            ),
            read_options=pacsv.ReadOptions(block_size=16 << 20),
        )
        batches, n, seen = [], 0, 0
        for batch in reader:
            # `seen` counts file rows before this batch, so both the stride
            # and the row numbers carry across batches.
            file_rows = batch.num_rows
            first = (-seen) % sample_every
            positions = pa.array(range(first, file_rows, sample_every), pa.int64())
            if sample_every > 1:
                batch = batch.take(positions)
            if row_number_column:
                row_numbers = pc.add(positions, pa.scalar(seen + 1, pa.int64()))
                batch = pa.RecordBatch.from_arrays(
                    [row_numbers, *batch.columns], names=[row_number_column, *batch.schema.names]
                )
            seen += file_rows
            batches.append(batch)
            n += batch.num_rows
            if limit and n >= limit:
                break
        table = pa.Table.from_batches(batches)
        if limit:
            table = table.slice(0, limit)

        self.create_schema(relation)
        self.drop_relation(relation)
        self._ingest(relation, table, mode="create")
        return table.num_rows

    @available
    def load_seed_table(self, relation: BaseRelation, agate_table: agate.Table) -> int:
        """Append an agate table (a seed) to an existing table via ADBC ingest.

        Used instead of dbt's batched, parameterized INSERTs because bulk
        ingest is much faster.
        """
        target = {c["column_name"]: c["xdbc_type_name"] for c in self._table_columns(relation.schema, relation.identifier)}
        arrays, names = [], []
        for name, column in zip(agate_table.column_names, agate_table.columns):
            if name not in target:
                raise DbtRuntimeError(f"Seed column {name} is missing from {relation}")
            arrow_type = _sql_to_arrow(target[name])
            values = [_to_py(v, arrow_type) for v in column.values()]
            try:
                arr = pa.array(values, type=arrow_type)
            except (pa.ArrowInvalid, pa.ArrowTypeError, TypeError):
                # Columns with a configured column_type reach us as text.
                arr = pa.array([None if v is None else str(v) for v in values], pa.string()).cast(arrow_type)
            arrays.append(arr)
            names.append(name)
        table = pa.Table.from_arrays(arrays, names=names)
        self._ingest(relation, table, mode="append")
        return table.num_rows


def _to_py(v, arrow_type: pa.DataType):
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        if pa.types.is_integer(arrow_type):
            return int(v)
        if pa.types.is_floating(arrow_type):
            return float(v)
    if isinstance(v, datetime.datetime) and pa.types.is_date(arrow_type):
        return v.date()
    if pa.types.is_string(arrow_type) and not isinstance(v, str):
        return str(v)
    return v
