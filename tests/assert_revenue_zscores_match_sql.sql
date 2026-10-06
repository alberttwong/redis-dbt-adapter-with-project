-- agg_daily_revenue_zscores (a Python model) agrees with the same z-scores
-- computed in SQL by the driver.
with sql_zscores as (
    select
        pickup_date,
        round((total_revenue - avg(total_revenue) over ()) / stddev_samp(total_revenue) over (), 3) as revenue_zscore
    from {{ ref('agg_daily_revenue') }}
)

select s.pickup_date, s.revenue_zscore as sql_zscore, p.revenue_zscore as python_zscore
from sql_zscores s
left join {{ ref('agg_daily_revenue_zscores') }} p on p.pickup_date = s.pickup_date
where p.pickup_date is null
   or abs(s.revenue_zscore - p.revenue_zscore) > 0.001
