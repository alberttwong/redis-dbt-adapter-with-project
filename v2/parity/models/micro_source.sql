{{ config(materialized='view', event_time='occurred_at', enabled=var('microbatch_demo', false)) }}
select 1 as id, cast('2024-01-01 12:00:00' as timestamp) as occurred_at
union all select 2, cast('2024-01-02 12:00:00' as timestamp)
