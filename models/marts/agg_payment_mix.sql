select
    payment_type_id,
    payment_type_name,
    count(*)                                                    as trips,
    round(count(*) * 100.0 / sum(count(*)) over (), 2)          as pct_of_trips,
    round(avg(total_amount), 2)                                 as avg_total,
    round(sum(tip_amount), 2)                                   as total_tips
from {{ ref('fct_trips') }}
group by payment_type_id, payment_type_name
order by trips desc
