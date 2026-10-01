{#- Trips to or from the three airports, by airport and direction. -#}

with airport_trips as (
    select
        case when is_airport_pickup then pickup_zone else dropoff_zone end         as airport,
        case when is_airport_pickup then 'from airport' else 'to airport' end      as direction,
        trip_distance,
        trip_duration_minutes,
        total_amount,
        tolls_amount
    from {{ ref('fct_trips') }}
    where is_airport_pickup or is_airport_dropoff
)

select
    airport,
    direction,
    count(*)                                    as trips,
    {{ round_to('avg(trip_distance)', 2) }}     as avg_miles,
    {{ round_to('avg(trip_duration_minutes)', 1) }} as avg_minutes,
    {{ round_to('avg(total_amount)', 2) }}      as avg_total,
    {{ round_to('avg(tolls_amount)', 2) }}      as avg_tolls
from airport_trips
group by airport, direction
order by trips desc
