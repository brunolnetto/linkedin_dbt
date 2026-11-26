-- A aba TOP POSTS tem duas listas lado a lado: top 50 por engajamento (A:C)
-- e top 50 por impressões (E:G). Viram linhas com ranking_metric.
with raw as (
    select * from {{ read_export_sheet('TOP POSTS', 'A3:G200') }}
)
select "A" as post_url, {{ parse_us_date('"B"') }} as published_date,
       'engagements' as ranking_metric, try_cast("C" as integer) as metric_value
from raw where "A" like 'http%'
union all
select "E", {{ parse_us_date('"F"') }}, 'impressions', try_cast("G" as integer)
from raw where "E" like 'http%'
