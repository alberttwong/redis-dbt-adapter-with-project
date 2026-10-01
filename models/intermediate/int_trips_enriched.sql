{#- Trips joined to their pickup/dropoff zones and lookup descriptions.
    The driver runs these as hash joins in memory. -#}

with trips as (
    select * from {{ ref('stg_yellow_trips') }}
),

zones as (
    select * from {{ ref('stg_taxi_zones') }}
)

select
    t.trip_id,
    t.vendor_id,
    coalesce(v.vendor_name, 'Unknown')          as vendor_name,
    t.pickup_datetime,
    t.dropoff_datetime,
    t.pickup_date,
    t.pickup_hour,
    t.pickup_iso_weekday,
    t.pickup_day_part,
    t.trip_duration_minutes,

    t.pickup_location_id,
    puz.borough                                  as pickup_borough,
    puz.zone_name                                as pickup_zone,
    puz.is_airport                               as is_airport_pickup,
    t.dropoff_location_id,
    doz.borough                                  as dropoff_borough,
    doz.zone_name                                as dropoff_zone,
    doz.is_airport                               as is_airport_dropoff,

    t.rate_code_id,
    coalesce(r.rate_code_name, 'Unknown')       as rate_code_name,
    t.payment_type_id,
    coalesce(p.payment_type_name, 'Unknown')    as payment_type_name,

    t.passenger_count,
    t.trip_distance,
    t.is_store_and_forward,
    t.fare_amount,
    t.extra,
    t.mta_tax,
    t.tip_amount,
    t.tolls_amount,
    t.improvement_surcharge,
    t.congestion_surcharge,
    t.total_amount,
    -- Tips are only recorded for card payments.
    case
        when t.payment_type_id = 1 and t.fare_amount > 0
        then {{ round_to('t.tip_amount * 100.0 / t.fare_amount', 2) }}
    end                                         as tip_pct,
    case
        when t.trip_duration_minutes > 0
        then {{ round_to('t.trip_distance * 60.0 / t.trip_duration_minutes', 2) }}
    end                                         as avg_mph

from trips t
left join zones puz on t.pickup_location_id = puz.location_id
left join zones doz on t.dropoff_location_id = doz.location_id
left join {{ ref('stg_payment_types') }} p on t.payment_type_id = p.payment_type_id
left join {{ ref('stg_rate_codes') }} r on t.rate_code_id = r.rate_code_id
left join {{ ref('stg_vendors') }} v on t.vendor_id = v.vendor_id
