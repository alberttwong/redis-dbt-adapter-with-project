{#- Nearly all of dbt's default relation macros work on the driver as-is
    (CREATE TABLE … AS, CREATE VIEW, ALTER … RENAME, DROP … CASCADE,
    TRUNCATE, temporary tables, MERGE). What's left here: -#}

{#- Temporary tables live in the connection's own schema and are referenced
    unqualified (a schema-qualified name always means a permanent table),
    as on Postgres. -#}
{% macro redis_adbc__make_temp_relation(base_relation, suffix) -%}
  {%- set tmp_identifier = base_relation.identifier ~ suffix -%}
  {{ return(base_relation.incorporate(path={"identifier": tmp_identifier}).include(database=False, schema=False)) }}
{%- endmacro %}

{#- dbt show / --limit: wrap the query so that a model with its own LIMIT
    still works. -#}
{% macro redis_adbc__get_limit_sql(sql, limit) -%}
  {%- if limit is none -%}
    {{ sql }}
  {%- else -%}
    select * from (
      {{ sql }}
    ) as dbt_limit_subq
    limit {{ limit }}
  {%- endif -%}
{%- endmacro %}

{#- The driver takes ? parameters (dbt's default is %s). -#}
{% macro redis_adbc__get_binding_char() -%}
  ?
{%- endmacro %}

{#- dbt's default is deliberately unimplemented; the driver has it natively. -#}
{% macro redis_adbc__current_timestamp() -%}
  current_timestamp
{%- endmacro %}

{#- Some of dbt's macros (snapshots with hard_deletes: new_record) call the
    get_columns_in_relation macro rather than the adapter method. -#}
{% macro redis_adbc__get_columns_in_relation(relation) -%}
  {{ return(adapter.get_columns_in_relation(relation)) }}
{%- endmacro %}

{#- Snapshot validity timestamps without a time zone (UTC), as on Postgres,
    so they compare with the usual TIMESTAMP updated_at columns. -#}
{% macro redis_adbc__snapshot_get_time() -%}
  localtimestamp
{%- endmacro %}

{#- dbt calls the adapter method; packages and user code call the macro. -#}
{% macro redis_adbc__list_relations_without_caching(schema_relation) -%}
  {{ return(adapter.list_relations_table(schema_relation)) }}
{%- endmacro %}
