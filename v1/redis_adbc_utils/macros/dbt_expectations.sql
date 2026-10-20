{#- The driver's REGEXP_INSTR takes Postgres 15's arguments, flags included
    (dbt_expectations' default ignores flags; its Postgres version needs
    arrays). These are the flags the driver supports. -#}
{% macro redis_adbc__regexp_instr(source_value, regexp, position, occurrence, is_raw, flags) %}
{% if flags %}{{ dbt_expectations._validate_flags(flags, 'icnmspwq') }}{% endif %}
regexp_instr({{ source_value }}, '{{ regexp }}', {{ position }}, {{ occurrence }}, 0, '{{ flags }}')
{% endmacro %}
