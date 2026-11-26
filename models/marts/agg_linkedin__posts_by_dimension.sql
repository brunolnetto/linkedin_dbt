-- Medianas por tema, idioma, formato e dia da semana (formato longo).
{% set dims = ['topic', 'language', 'post_format', 'published_weekday'] %}
{% for dim in dims %}
select
    '{{ dim }}'                     as dimension,
    {{ dim }}                       as dimension_value,
    count(*)                        as posts,
    sum(impressions)                as impressions_total,
    median(impressions)             as impressions_median,
    median(engagements)             as engagements_median,
    median(engagement_rate)         as engagement_rate_median,
    median(followers_in_window)     as followers_in_window_median
from {{ ref('fct_linkedin__posts') }}
group by {{ dim }}
{% if not loop.last %}union all{% endif %}
{% endfor %}
