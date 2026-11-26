select
    {{ parse_us_date('"A"') }}       as activity_date,
    try_cast("B" as integer)         as impressions,
    try_cast("C" as integer)         as engagements
from {{ read_export_sheet('ENGAGEMENT', 'A2:C2000') }}
where {{ parse_us_date('"A"') }} is not null
