{% macro assert_query(sql, expected) %}
  {% set actual = run_query(sql).rows[0][0] %}
  {% if actual | int != expected | int %}
    {{ exceptions.raise_compiler_error('Parity assertion failed: ' ~ sql ~ '; expected ' ~ expected ~ ', got ' ~ actual) }}
  {% endif %}
{% endmacro %}

{% macro mutate_trips() %}
  {% do run_query('update ' ~ ref('trips') ~ " set zone = 'updated' where id = 1") %}
  {% do run_query('delete from ' ~ ref('trips') ~ ' where id = 2') %}
{% endmacro %}

{% macro load_parity_csv(path) %}
  {% set relation = api.Relation.create(database=target.database, schema=target.schema, identifier='csv_sample', type='table') %}
  {% set n = adapter.load_csv_file(relation, path, {'id': 'BIGINT', 'name': 'VARCHAR'}, sample_every=2, limit=2, row_number_column='file_row') %}
  {% if n != 2 %}{{ exceptions.raise_compiler_error('Expected two sampled CSV rows') }}{% endif %}
{% endmacro %}

{% macro violate_contract() %}
  {% do run_query('insert into ' ~ ref('trips_contract') ~ " (id, zone) values (null, 'invalid')") %}
{% endmacro %}
