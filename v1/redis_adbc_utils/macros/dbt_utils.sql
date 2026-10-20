{#- dbt_utils' default joins the relation to its row-numbered self with a
    natural join, which drops every row with a NULL in any column. Postgres's
    DISTINCT ON version works on the driver. -#}
{%- macro redis_adbc__deduplicate(relation, partition_by, order_by) -%}
  {{ return(dbt_utils.postgres__deduplicate(relation, partition_by, order_by)) }}
{%- endmacro %}
