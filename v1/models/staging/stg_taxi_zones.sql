select
    LocationID      as location_id,
    Borough         as borough,
    Zone            as zone_name,
    service_zone,
    case when Zone like '%Airport%' then true else false end as is_airport
from {{ ref('taxi_zone_lookup') }}
