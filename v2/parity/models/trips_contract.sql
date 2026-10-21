{{ config(materialized='table', contract={'enforced': true}, persist_docs={'relation': true, 'columns': true}) }}
select id, zone from {{ ref('trips_input') }}
