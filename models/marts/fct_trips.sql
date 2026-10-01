{#- Trip fact table, built incrementally with delete+insert on trip_id.
    Each run reloads the last `lookback_hours` before the latest pickup
    already in the table (to pick up late-arriving trips) plus everything
    after it. -#}

{{ config(materialized='incremental', unique_key='trip_id') }}

select *
from {{ ref('int_trips_enriched') }}

{% if is_incremental() %}
where pickup_datetime >= (
    select max(pickup_datetime) - interval '{{ var("lookback_hours") }} hours' from {{ this }}
)
{% endif %}
