select
    payment_type_id,
    payment_type_name,
    count(*)                                                                    as trips,
    {{ round_to('count(*) * 100.0 / (select count(*) from ' ~ ref('fct_trips') ~ ')', 2) }} as pct_of_trips,
    {{ round_to('avg(total_amount)', 2) }}                                      as avg_total,
    {{ round_to('sum(tip_amount)', 2) }}                                        as total_tips
from {{ ref('fct_trips') }}
group by payment_type_id, payment_type_name
order by trips desc
