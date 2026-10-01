{#- TLC-style day part for a timestamp. -#}
{% macro day_part(ts) -%}
  case
    when extract(hour from {{ ts }}) < 6 then 'overnight'
    when extract(hour from {{ ts }}) < 10 then 'morning rush'
    when extract(hour from {{ ts }}) < 16 then 'midday'
    when extract(hour from {{ ts }}) < 20 then 'evening rush'
    else 'night'
  end
{%- endmacro %}

{#- Round to `scale` decimals. The driver has no ROUND() yet
    (alberttwong/redis-adbc-driver#24), but CAST to NUMERIC rounds. -#}
{% macro round_to(expr, scale=2) -%}
  cast({{ expr }} as numeric(18, {{ scale }}))
{%- endmacro %}
