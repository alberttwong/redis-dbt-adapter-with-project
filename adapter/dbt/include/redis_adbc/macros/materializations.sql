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

{#- Microbatch: each batch replaces the target's rows in its event_time
    window [event_time_start, event_time_end), then inserts the batch. The
    bounds are written like dbt's own filter on upstream refs, so the window
    deleted is exactly the one the batch was read from. -#}
{% macro redis_adbc__get_incremental_microbatch_sql(arg_dict) %}
  {%- set target = arg_dict["target_relation"] -%}
  {%- set source = arg_dict["temp_relation"] -%}
  {%- set dest_columns = arg_dict["dest_columns"] -%}
  {%- set predicates = (arg_dict.get("incremental_predicates") or []) | list -%}
  {%- set event_time = model.config.event_time -%}
  {%- if model.batch and model.batch.event_time_start -%}
    {%- do predicates.append("DBT_INTERNAL_TARGET." ~ event_time ~ " >= '" ~ model.batch.event_time_start ~ "'") -%}
  {%- endif -%}
  {%- if model.batch and model.batch.event_time_end -%}
    {%- do predicates.append("DBT_INTERNAL_TARGET." ~ event_time ~ " < '" ~ model.batch.event_time_end ~ "'") -%}
  {%- endif -%}
  {%- if not predicates -%}
    {{ exceptions.raise_compiler_error("microbatch: no batch window for " ~ target ~ "; refusing to delete every row") }}
  {%- endif -%}
  {%- set cols = get_quoted_csv(dest_columns | map(attribute="name")) %}
  delete from {{ target }} as DBT_INTERNAL_TARGET
  where {{ predicates | join("\n    and ") }};
  insert into {{ target }} ({{ cols }})
  (
    select {{ cols }} from {{ source }}
  )
{% endmacro %}

{#- Redis has no materialized views; say so instead of dbt's "not implemented"
    errors (or, for a table switched to materialized_view, a rename error). -#}
{% materialization materialized_view, adapter='redis_adbc' %}
  {{ exceptions.raise_compiler_error("materialized views aren't supported on Redis (" ~ this ~ "); use materialized='table' or 'incremental'") }}
{% endmaterialization %}
