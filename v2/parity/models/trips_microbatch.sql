{{ config(materialized='incremental', incremental_strategy='microbatch', event_time='occurred_at', begin='2024-01-01', batch_size='day', enabled=var('microbatch_demo', false)) }}
select * from {{ ref('micro_source') }}
