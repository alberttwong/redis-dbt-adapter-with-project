{% macro drop_smoke_schema() %}
  {% if not target.schema.startswith('dbt_v2_parity_') %}
    {{ exceptions.raise_compiler_error('Refusing to drop a schema outside the v2 parity namespace') }}
  {% endif %}
  {% do adapter.drop_schema(api.Relation.create(database=target.database, schema=target.schema)) %}
{% endmacro %}
