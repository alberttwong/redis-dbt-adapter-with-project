{#- The trip fact table as a microbatch incremental model: one batch per
    pickup day, each replacing that day's rows. Off by default; see
    `make microbatch-demo`. dbt reads only the batch's day from
    int_trips_enriched (its event_time is pickup_datetime). -#}

{{ config(
    enabled=var('microbatch_demo', false),
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='pickup_datetime',
    batch_size='day',
    begin='2019-01-01',
    lookback=1,
    concurrent_batches=true,
) }}

select trip_id, pickup_datetime, pickup_date, pickup_borough, payment_type_name, total_amount
from {{ ref('int_trips_enriched') }}
