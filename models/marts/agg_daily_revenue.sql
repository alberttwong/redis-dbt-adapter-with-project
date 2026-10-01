select
    pickup_date,
    min(pickup_iso_weekday)                                     as iso_weekday,
    count(*)                                                    as trips,
    sum(passenger_count)                                        as passengers,
    {{ round_to('sum(trip_distance)', 1) }}                     as total_miles,
    {{ round_to('sum(fare_amount)', 2) }}                       as fare_revenue,
    {{ round_to('sum(tip_amount)', 2) }}                        as tip_revenue,
    {{ round_to('sum(total_amount)', 2) }}                      as total_revenue,
    {{ round_to('avg(total_amount)', 2) }}                      as avg_total_per_trip,
    {{ round_to('avg(trip_distance)', 2) }}                     as avg_miles_per_trip,
    {{ round_to('avg(trip_duration_minutes)', 1) }}             as avg_minutes_per_trip,
    {{ round_to('avg(tip_pct)', 2) }}                           as avg_card_tip_pct,
    {{ round_to('sum(total_amount) / sum(trip_distance)', 2) }} as revenue_per_mile
from {{ ref('fct_trips') }}
group by pickup_date
order by pickup_date
