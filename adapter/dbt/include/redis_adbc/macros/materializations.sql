{#- Tables use dbt's default materialization: CTAS into `<name>__dbt_tmp`,
    then ALTER TABLE ... RENAME to swap it in.

    Views: the driver can't rename a view (ALTER TABLE only finds tables), so
    dbt's rename-swap doesn't work. CREATE OR REPLACE VIEW does, and is atomic. -#}

{% macro redis_adbc__build_table(target_relation, sql) %}
  {%- set existing_relation = load_cached_relation(this) -%}

  {{ run_hooks(pre_hooks) }}

  {% if existing_relation is not none %}
    {{ adapter.drop_relation(existing_relation) }}
  {% endif %}

  {% call statement('main') -%}
    {{ get_create_table_as_sql(False, target_relation, sql) }}
  {%- endcall %}

  {{ run_hooks(post_hooks) }}
{% endmacro %}


{% materialization view, adapter='redis_adbc' %}
  {%- set target_relation = this.incorporate(type='view') -%}
  {%- set existing_relation = load_cached_relation(this) -%}

  {{ run_hooks(pre_hooks) }}

  {% if existing_relation is not none and not existing_relation.is_view %}
    {{ adapter.drop_relation(existing_relation) }}
  {% endif %}

  {% call statement('main') -%}
    create or replace view {{ target_relation }} as
    {{ sql }}
  {%- endcall %}

  {{ run_hooks(post_hooks) }}
  {{ return({'relations': [target_relation]}) }}
{% endmaterialization %}


{#- Incremental: new rows are staged in `<name>__dbt_tmp` first so that an
    `is_incremental()` filter reading {{ this }} sees the table before any
    change. With a unique_key, matching rows are deleted before the insert
    (delete+insert). on_schema_change is not supported: the target keeps
    its columns and new rows are inserted by column name. -#}
{% materialization incremental, adapter='redis_adbc' %}
  {%- set target_relation = this.incorporate(type='table') -%}
  {%- set existing_relation = load_cached_relation(this) -%}
  {%- set unique_key = config.get('unique_key') -%}
  {%- set full_refresh_mode = should_full_refresh() -%}

  {% if existing_relation is none or full_refresh_mode %}
    {{ redis_adbc__build_table(target_relation, sql) }}
  {% else %}
    {%- set tmp_relation = make_temp_relation(target_relation).incorporate(type='table') -%}

    {{ run_hooks(pre_hooks) }}

    {{ adapter.drop_relation(tmp_relation) }}
    {% call statement('stage') -%}
      {{ get_create_table_as_sql(False, tmp_relation, sql) }}
    {%- endcall %}

    {%- set dest_columns = adapter.get_columns_in_relation(existing_relation) -%}
    {%- set dest_cols_csv = dest_columns | map(attribute='name') | join(', ') -%}

    {%- set keys = ([unique_key] if unique_key is string else unique_key) if unique_key else [] -%}
    {% if keys %}
      {#- Find the keys that already exist with a hash join, and delete only
          those. The driver is much slower at a large IN (SELECT ...) than at
          a join, and a plain append matches nothing. -#}
      {%- set matched_relation = make_temp_relation(target_relation, '__dbt_matched').incorporate(type='table') -%}
      {{ adapter.drop_relation(matched_relation) }}
      {% call statement('match_keys') -%}
        create table {{ matched_relation }} as
        select {% for k in keys %}dbt_old.{{ k }}{{ ", " if not loop.last }}{% endfor %}
        from {{ target_relation }} dbt_old
        join {{ tmp_relation }} dbt_new
          on {% for k in keys -%}
            dbt_new.{{ k }} = dbt_old.{{ k }}{{ " and " if not loop.last }}
          {%- endfor %}
      {%- endcall %}
      {%- set matched = run_query("select count(*) from " ~ matched_relation).columns[0].values()[0] -%}

      {% if matched > 0 %}
        {% call statement('delete_matched') -%}
          delete from {{ target_relation }}
          {% if keys | length == 1 -%}
          where {{ keys[0] }} in (select {{ keys[0] }} from {{ matched_relation }})
          {%- else -%}
          where exists (
            select 1 from {{ matched_relation }} dbt_m
            where {% for k in keys -%}
              dbt_m.{{ k }} = {{ target_relation }}.{{ k }}{{ " and " if not loop.last }}
            {%- endfor %}
          )
          {%- endif %}
        {%- endcall %}
      {% endif %}
      {{ adapter.drop_relation(matched_relation) }}
    {% endif %}

    {% call statement('main') -%}
      insert into {{ target_relation }} ({{ dest_cols_csv }})
      select {{ dest_cols_csv }} from {{ tmp_relation }}
    {%- endcall %}

    {{ adapter.drop_relation(tmp_relation) }}

    {{ run_hooks(post_hooks) }}
  {% endif %}

  {% do persist_docs(target_relation, model) %}
  {{ return({'relations': [target_relation]}) }}
{% endmaterialization %}


{#- Seeds: dbt's default loader sends batched, parameterized INSERTs.
    Load the rows with ADBC bulk ingest instead (see load_seed_table). -#}
{% macro redis_adbc__load_csv_rows(model, agate_table) %}
  {%- set relation = api.Relation.create(database=model['database'], schema=model['schema'], identifier=model['alias'], type='table') -%}
  {%- set n = adapter.load_seed_table(relation, agate_table) -%}
  {{ return("-- " ~ n ~ " rows loaded with ADBC bulk ingest") }}
{% endmacro %}
