{#- Average demand by hour of day across the month. -#}

select
    pickup_hour,
    pickup_day_part,
    count(*)                                            as trips,
    {{ round_to('count(*) * 1.0 / count(distinct pickup_date)', 1) }} as avg_trips_per_day,
    {{ round_to('avg(trip_distance)', 2) }}             as avg_miles,
    {{ round_to('avg(trip_duration_minutes)', 1) }}     as avg_minutes,
    {{ round_to('avg(avg_mph)', 1) }}                   as avg_mph,
    {{ round_to('avg(total_amount)', 2) }}              as avg_total,
    {{ round_to('avg(tip_pct)', 2) }}                   as avg_card_tip_pct
from {{ ref('fct_trips') }}
group by pickup_hour, pickup_day_part
order by pickup_hour
