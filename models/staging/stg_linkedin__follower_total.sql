select
    try_strptime(regexp_extract("A", '(\d{1,2}/\d{1,2}/\d{4})', 1), '%m/%d/%Y')::date as snapshot_date,
    try_cast("B" as integer) as total_followers
from {{ read_export_sheet('FOLLOWERS', 'A1:B1') }}
