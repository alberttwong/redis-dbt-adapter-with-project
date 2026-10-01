{#- Per pickup date, with a 7-day rolling average and the change from the
    previous day (window functions over the grouped rows). -#}

with daily as (
    select
        pickup_date,
        min(pickup_iso_weekday)                 as iso_weekday,
        count(*)                                as trips,
        sum(passenger_count)                    as passengers,
        round(sum(trip_distance), 1)            as total_miles,
        round(sum(fare_amount), 2)              as fare_revenue,
        round(sum(tip_amount), 2)               as tip_revenue,
        round(sum(total_amount), 2)             as total_revenue,
        round(avg(total_amount), 2)             as avg_total_per_trip,
        round(avg(trip_distance), 2)            as avg_miles_per_trip,
        round(avg(trip_duration_minutes), 1)    as avg_minutes_per_trip,
        round(avg(tip_pct), 2)                  as avg_card_tip_pct,
        round(sum(total_amount) / sum(trip_distance), 2) as revenue_per_mile
    from {{ ref('fct_trips') }}
    group by pickup_date
)

select
    *,
    round(avg(total_revenue) over (
        order by pickup_date rows between 6 preceding and current row
    ), 2)                                                       as revenue_7d_avg,
    trips - lag(trips) over (order by pickup_date)              as trips_vs_prev_day,
    rank() over (order by total_revenue desc)                   as revenue_rank
from daily
order by pickup_date
