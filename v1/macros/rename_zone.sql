{#- Change a zone's name in the taxi_zone_lookup seed table, to see
    `dbt snapshot` record the change (`make snapshot-demo`).

    dbt run-operation rename_zone --args '{location_id: 132, name: "JFK International Airport"}'

    `dbt seed` restores the original lookup. -#}

{% macro rename_zone(location_id, name) %}
  {% call statement('rename_zone') -%}
    update {{ ref('taxi_zone_lookup') }} set Zone = '{{ name | replace("'", "''") }}' where LocationID = {{ location_id }}
  {%- endcall %}
  {{ log("Zone " ~ location_id ~ " is now " ~ name, info=True) }}
{% endmacro %}
