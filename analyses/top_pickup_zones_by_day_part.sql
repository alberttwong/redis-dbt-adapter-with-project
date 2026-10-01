-- `dbt compile` renders this to target/compiled/; run it with
-- dbt show -s top_pickup_zones_by_day_part
select
    pickup_day_part,
    pickup_borough,
    pickup_zone,
    count(*)                                as trips,
    {{ round_to('avg(total_amount)', 2) }}  as avg_total
from {{ ref('fct_trips') }}
group by pickup_day_part, pickup_borough, pickup_zone
having count(*) >= 500
order by trips desc
limit 20
