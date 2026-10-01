{#- Trips between boroughs, keeping flows with at least `min_trips` trips. -#}

{% set min_trips = 25 %}

select
    pickup_borough,
    dropoff_borough,
    count(*)                                    as trips,
    round(avg(trip_distance), 2)                as avg_miles,
    round(avg(total_amount), 2)                 as avg_total,
    round(sum(total_amount), 2)                 as total_revenue
from {{ ref('fct_trips') }}
group by pickup_borough, dropoff_borough
having count(*) >= {{ min_trips }}
order by trips desc
