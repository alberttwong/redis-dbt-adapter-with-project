{#- The busiest pickup zones in each borough: RANK() per borough, kept with
    QUALIFY. -#}

select
    pickup_borough,
    pickup_zone,
    count(*)                                                    as trips,
    round(sum(total_amount), 2)                                 as total_revenue,
    rank() over (partition by pickup_borough order by count(*) desc) as borough_rank
from {{ ref('fct_trips') }}
where pickup_borough not in ('Unknown', 'N/A')
group by pickup_borough, pickup_zone
qualify rank() over (partition by pickup_borough order by count(*) desc) <= {{ var('top_zones_per_borough') }}
order by pickup_borough, borough_rank, pickup_zone
