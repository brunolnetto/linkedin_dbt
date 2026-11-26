{#- Em cargas incrementais, ignora exports que já estão na tabela (a menos que force_reload).
    Evita apagar e regravar o mesmo bloco, que faz o arquivo do banco crescer à toa. -#}
{% macro skip_loaded_exports(export_id_col='x.export_id') -%}
{% if is_incremental() and not var('force_reload', false) -%}
{{ export_id_col }} not in (select export_id from {{ this }})
{%- else -%}
true
{%- endif %}
{%- endmacro %}
