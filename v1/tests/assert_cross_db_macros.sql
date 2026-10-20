-- dbt's cross-database macros return what dbt documents for them on this
-- adapter. Any row returned is a failure.
with scalars as (
    select
        cast({{ dbt.dateadd('day', 1, "date '2019-01-31'") }} as date)      as next_day,
        {{ dbt.datediff("date '2019-01-01'", "date '2019-02-01'", 'day') }} as days_between,
        {{ dbt.last_day("date '2019-02-10'", 'month') }}                     as month_end,
        {{ dbt.safe_cast("'not a number'", api.Column.translate_type('integer')) }} as bad_int,
        {{ dbt.safe_cast("'42'", api.Column.translate_type('integer')) }}           as good_int
),

aggregates as (
    select
        {{ dbt.listagg('vendor_name', "', '", 'order by vendor_id') }} as vendor_names,
        {{ dbt.bool_or('vendor_id = 2') }}                             as has_vendor_2,
        {{ dbt.any_value('vendor_id') }}                               as some_vendor
    from {{ ref('stg_vendors') }}
),

spine as (
    select count(*) as days
    from ({{ dbt.date_spine('day', "date '2019-01-01'", "date '2019-02-01'") }}) d
)

select 'dateadd' as macro from scalars where next_day <> date '2019-02-01'
union all select 'datediff' from scalars where days_between <> 31
union all select 'last_day' from scalars where month_end <> date '2019-02-28'
union all select 'safe_cast (bad value)' from scalars where bad_int is not null
union all select 'safe_cast (good value)' from scalars where good_int <> 42
union all select 'listagg' from aggregates where vendor_names <> 'Creative Mobile Technologies, VeriFone'
union all select 'bool_or' from aggregates where not has_vendor_2
union all select 'any_value' from aggregates where some_vendor not in (1, 2)
union all select 'date_spine' from spine where days <> 31
