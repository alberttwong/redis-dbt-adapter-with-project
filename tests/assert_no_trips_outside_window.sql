select trip_id, pickup_datetime
from {{ ref('fct_trips') }}
where pickup_datetime < timestamp '{{ var("trips_start") }}'
   or pickup_datetime >= timestamp '{{ var("trips_end") }}'
