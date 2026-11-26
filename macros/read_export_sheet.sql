{#- Lê uma aba do export .xlsx do LinkedIn como texto bruto (colunas A, B, C...). -#}
{% macro read_export_sheet(sheet, range) -%}
read_xlsx(
    '{{ var("linkedin_export") }}',
    sheet = '{{ sheet }}',
    range = '{{ range }}',
    header = false,
    all_varchar = true,
    stop_at_empty = false
)
{%- endmacro %}

{#- Converte '60%' -> 0.60 e '< 1%' -> null (use is_below_1pct para a flag) -#}
{% macro parse_pct(col) -%}
case when {{ col }} like '<%' then null
     else try_cast(replace(trim({{ col }}), '%', '') as double) / 100 end
{%- endmacro %}

{% macro parse_us_date(col) -%}
try_strptime(trim({{ col }}), '%m/%d/%Y')::date
{%- endmacro %}
