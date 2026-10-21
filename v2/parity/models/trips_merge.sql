{{ config(materialized='incremental', unique_key='id', incremental_strategy='merge') }}
select * from {{ ref('trips_input') }}
