{#- Taxi zones with their pickup/dropoff activity. -#}

with pickups as (
    select pickup_location_id as location_id, count(*) as pickups, sum(total_amount) as pickup_revenue
    from {{ ref('fct_trips') }}
    group by pickup_location_id
),

dropoffs as (
    select dropoff_location_id as location_id, count(*) as dropoffs
    from {{ ref('fct_trips') }}
    group by dropoff_location_id
)

select
    z.location_id,
    z.borough,
    z.zone_name,
    z.service_zone,
    z.is_airport,
    coalesce(p.pickups, 0)                                  as pickups,
    coalesce(d.dropoffs, 0)                                 as dropoffs,
    round(coalesce(p.pickup_revenue, 0), 2)     as pickup_revenue
from {{ ref('stg_taxi_zones') }} z
left join pickups p on z.location_id = p.location_id
left join dropoffs d on z.location_id = d.location_id
