{#- Tables, views, incremental models and snapshots use dbt's default
    materializations. -#}

{#- Incremental models: with a unique_key the default strategy is
    delete+insert (as on Postgres), otherwise append. merge is also
    available. -#}
{% macro redis_adbc__get_incremental_default_sql(arg_dict) -%}
  {%- if arg_dict["unique_key"] -%}
    {{ return(get_incremental_delete_insert_sql(arg_dict)) }}
  {%- else -%}
    {{ return(get_incremental_append_sql(arg_dict)) }}
  {%- endif -%}
{%- endmacro %}

{#- Seeds: load the rows with ADBC bulk ingest (see load_seed_table), which
    is much faster than dbt's batched, parameterized INSERTs. -#}
{% macro redis_adbc__load_csv_rows(model, agate_table) %}
  {%- set relation = api.Relation.create(database=model['database'], schema=model['schema'], identifier=model['alias'], type='table') -%}
  {%- set n = adapter.load_seed_table(relation, agate_table) -%}
  {{ return("-- " ~ n ~ " rows loaded with ADBC bulk ingest") }}
{% endmacro %}
