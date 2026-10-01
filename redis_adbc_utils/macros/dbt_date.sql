{#- dbt_date's defaults are written for Snowflake (padded TO_CHAR names,
    Monday-start weeks, the `isoweek` unit). The driver follows Postgres,
    so use dbt_date's Postgres versions. -#}

{%- macro redis_adbc__day_name(date, short, language) -%}
  {{ return(dbt_date.postgres__day_name(date, short, language)) }}
{%- endmacro %}

{%- macro redis_adbc__month_name(date, short, language) -%}
  {{ return(dbt_date.postgres__month_name(date, short, language)) }}
{%- endmacro %}

{%- macro redis_adbc__week_start(date) -%}
  {{ return(dbt_date.postgres__week_start(date)) }}
{%- endmacro %}

{%- macro redis_adbc__week_end(date) -%}
  {{ return(dbt_date.postgres__week_end(date)) }}
{%- endmacro %}

{%- macro redis_adbc__iso_week_start(date) -%}
  {{ return(dbt_date.postgres__iso_week_start(date)) }}
{%- endmacro %}

{%- macro redis_adbc__iso_week_of_year(date) -%}
  {{ return(dbt_date.postgres__iso_week_of_year(date)) }}
{%- endmacro %}

{%- macro redis_adbc__week_of_year(date) -%}
  {{ return(dbt_date.postgres__week_of_year(date)) }}
{%- endmacro %}
