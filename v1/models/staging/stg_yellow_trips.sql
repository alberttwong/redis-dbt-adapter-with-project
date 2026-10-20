{#- One row per trip: renamed to snake_case, typed, and filtered to valid
    trips inside the configured window. A single-table view, so the driver
    expands it in place and pushes filters into the raw table's index. -#}

select
    trip_id,
    VendorID                                    as vendor_id,
    RatecodeID                                  as rate_code_id,
    PULocationID                                as pickup_location_id,
    DOLocationID                                as dropoff_location_id,
    payment_type                                as payment_type_id,

    tpep_pickup_datetime                        as pickup_datetime,
    tpep_dropoff_datetime                       as dropoff_datetime,
    cast(tpep_pickup_datetime as date)          as pickup_date,
    extract(hour from tpep_pickup_datetime)     as pickup_hour,
    extract(isodow from tpep_pickup_datetime)   as pickup_iso_weekday,
    {{ day_part('tpep_pickup_datetime') }}      as pickup_day_part,
    round(extract(epoch from tpep_dropoff_datetime - tpep_pickup_datetime) / 60.0, 2) as trip_duration_minutes,

    passenger_count,
    trip_distance,
    case when store_and_fwd_flag = 'Y' then true else false end as is_store_and_forward,

    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    coalesce(congestion_surcharge, 0)           as congestion_surcharge,
    total_amount

from {{ source('nyc_tlc', 'yellow_tripdata') }}
where tpep_pickup_datetime >= timestamp '{{ var("trips_start") }}'
  and tpep_pickup_datetime <  timestamp '{{ var("trips_end") }}'
  -- Drop zero/negative durations and meters left running for over 12 hours.
  and tpep_dropoff_datetime >  tpep_pickup_datetime
  and tpep_dropoff_datetime <= tpep_pickup_datetime + interval '12 hours'
  and trip_distance >= 0
  and total_amount >= 0
  -- The TLC data has a few garbage fares (e.g. $623,259 for 2.4 miles).
  and total_amount <= {{ var('max_total_amount') }}
