-- The daily rollup must account for every trip and every dollar in fct_trips.
with daily as (
    select sum(trips) as trips, sum(total_revenue) as revenue
    from {{ ref('agg_daily_revenue') }}
),

trips as (
    select count(*) as trips, sum(total_amount) as revenue
    from {{ ref('fct_trips') }}
)

select daily.trips as daily_trips, trips.trips as fct_trips,
       daily.revenue as daily_revenue, trips.revenue as fct_revenue
from daily, trips
where daily.trips <> trips.trips
   or abs(daily.revenue - trips.revenue) > 1
