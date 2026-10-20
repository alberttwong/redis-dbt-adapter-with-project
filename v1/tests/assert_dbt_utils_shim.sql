-- dbt_utils.deduplicate goes through redis_adbc_utils: every partition keeps
-- one row, including rows with NULLs (dbt_utils' default drops those).
with src as (
    select 1 as id, cast(null as varchar) as note, 1 as v
    union all select 1, cast(null as varchar), 2
    union all select 2, 'x', 1
    union all select 3, cast(null as varchar), 1
),

deduped as (
    {{ dbt_utils.deduplicate(relation='src', partition_by='id', order_by='v desc') }}
)

select * from (
    select count(*) as n, sum(v) as v_total from deduped
) as c
where n <> 3 or v_total <> 4
