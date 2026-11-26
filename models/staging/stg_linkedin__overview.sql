select
    max(case when "A" = 'Impressions' then try_cast("B" as integer) end)     as impressions,
    max(case when "A" = 'Members reached' then try_cast("B" as integer) end) as members_reached,
    max(case when "A" = 'Overall Performance' then "B" end)                  as period_label
from {{ read_export_sheet('DISCOVERY', 'A1:B10') }}
