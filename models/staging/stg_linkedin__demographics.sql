{% set sheets = [('AUDIENCE DEMOGRAPHICS', 'followers'), ('CONTENT DEMOGRAPHICS', 'content_viewers')] %}
{% for sheet, audience in sheets %}
select
    '{{ audience }}'                  as audience,
    "A"                               as dimension,
    "B"                               as dimension_value,
    "C"                               as share_label,
    {{ parse_pct('"C"') }}            as share,
    "C" like '<%'                     as is_below_1pct
from {{ read_export_sheet(sheet, 'A2:C500') }}
where "A" is not null and "B" is not null
{% if not loop.last %}union all{% endif %}
{% endfor %}
