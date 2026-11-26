select
    {{ parse_us_date('"A"') }}       as activity_date,
    try_cast("B" as integer)         as new_followers
from {{ read_export_sheet('FOLLOWERS', 'A3:B2000') }}
where {{ parse_us_date('"A"') }} is not null
