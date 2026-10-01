{#- Relation DDL. Driver gaps worked around here: no TRUNCATE (#23), no
    transactions, views can't be renamed (#22), DROP SCHEMA has no CASCADE
    (#23). Issue numbers refer to alberttwong/redis-adbc-driver. -#}

{% macro redis_adbc__create_schema(relation) -%}
  {%- call statement('create_schema') -%}
    create schema if not exists {{ relation.without_identifier() }}
  {%- endcall -%}
{% endmacro %}

{% macro redis_adbc__drop_schema(relation) -%}
  {%- call statement('drop_schema') -%}
    drop schema if exists {{ relation.without_identifier() }}
  {%- endcall -%}
{% endmacro %}

{% macro redis_adbc__drop_relation(relation) -%}
  {% call statement('drop_relation', auto_begin=False) -%}
    drop {{ 'view' if relation.is_view else 'table' }} if exists {{ relation }}
  {%- endcall %}
{% endmacro %}

{% macro redis_adbc__truncate_relation(relation) -%}
  {% call statement('truncate_relation') -%}
    delete from {{ relation }}
  {%- endcall %}
{% endmacro %}

{% macro redis_adbc__rename_relation(from_relation, to_relation) -%}
  {% if from_relation.is_view %}
    {{ exceptions.raise_compiler_error("The Redis ADBC driver cannot rename views") }}
  {% endif %}
  {% call statement('rename_relation') -%}
    alter table {{ from_relation }} rename to {{ to_relation.identifier }}
  {%- endcall %}
{% endmacro %}

{% macro redis_adbc__create_table_as(temporary, relation, compiled_code, language='sql') -%}
  {%- if language != 'sql' -%}
    {{ exceptions.raise_compiler_error("redis_adbc only supports SQL models") }}
  {%- endif -%}
  create table {{ relation }} as
  {{ compiled_code }}
{%- endmacro %}

{% macro redis_adbc__create_view_as(relation, sql) -%}
  create or replace view {{ relation }} as
  {{ sql }}
{%- endmacro %}

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

{% macro redis_adbc__get_binding_char() -%}
  ?
{%- endmacro %}
