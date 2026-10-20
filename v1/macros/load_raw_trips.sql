{#- Load the NYC TLC yellow-trips CSV into raw.yellow_tripdata.

    dbt run-operation load_raw_trips
    dbt run-operation load_raw_trips --args '{sample_every: 10, limit: 500000}'

    The CSV is streamed with pyarrow and written with ADBC bulk ingest (one
    Redis HASH per row plus a RediSearch index). The default keeps every 50th
    row so the sample spans the whole month. `trip_id` is each trip's row
    number in the CSV, so it stays the same across reloads and sample sizes. -#}

{% macro load_raw_trips(path=none, sample_every=none, limit=none) %}
  {%- set path = path or var('raw_trips_path') -%}
  {%- set sample_every = sample_every or var('raw_trips_sample_every') -%}
  {%- set limit = limit or var('raw_trips_limit') -%}
  {%- set relation = api.Relation.create(database=target.database, schema='raw', identifier='yellow_tripdata', type='table') -%}

  {#- Column types follow the TLC data dictionary. -#}
  {%- set column_types = {
      'VendorID': 'BIGINT',
      'tpep_pickup_datetime': 'TIMESTAMP',
      'tpep_dropoff_datetime': 'TIMESTAMP',
      'passenger_count': 'BIGINT',
      'trip_distance': 'DOUBLE PRECISION',
      'RatecodeID': 'BIGINT',
      'store_and_fwd_flag': 'VARCHAR',
      'PULocationID': 'BIGINT',
      'DOLocationID': 'BIGINT',
      'payment_type': 'BIGINT',
      'fare_amount': 'DOUBLE PRECISION',
      'extra': 'DOUBLE PRECISION',
      'mta_tax': 'DOUBLE PRECISION',
      'tip_amount': 'DOUBLE PRECISION',
      'tolls_amount': 'DOUBLE PRECISION',
      'improvement_surcharge': 'DOUBLE PRECISION',
      'total_amount': 'DOUBLE PRECISION',
      'congestion_surcharge': 'DOUBLE PRECISION',
  } -%}

  {{ log("Loading " ~ path ~ " into " ~ relation ~ " (every " ~ sample_every ~ " rows" ~ (", limit " ~ limit if limit else "") ~ ")", info=True) }}
  {%- set n = adapter.load_csv_file(relation, path, column_types, limit=limit, sample_every=sample_every, row_number_column='trip_id') -%}
  {{ log("Loaded " ~ n ~ " rows into " ~ relation, info=True) }}
{% endmacro %}
