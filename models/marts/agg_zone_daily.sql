{#- Trips and revenue per pickup zone and day. Incremental with a composite
    unique_key and no strategy, so the adapter's default delete+insert: each
    run replaces the days from the latest one already in the table on. -#}

{{ config(materialized='incremental', unique_key=['pickup_date', 'pickup_location_id']) }}

select
    pickup_date,
    pickup_location_id,
    count(*)                    as trips,
    round(sum(total_amount), 2) as revenue
from {{ ref('fct_trips') }}
{% if is_incremental() %}
where pickup_date >= (select max(pickup_date) from {{ this }})
{% endif %}
group by pickup_date, pickup_location_id
