select
    "A"                               as post_url,
    {{ parse_us_date('"B"') }}        as published_date,
    "C"                               as post_type,
    try_cast("D" as integer)          as impressions,
    {{ parse_pct('"E"') }}            as pct_in_network,
    {{ parse_pct('"F"') }}            as pct_out_of_network,
    try_cast("G" as integer)          as members_reached,
    try_cast("H" as integer)          as followers_gained,
    try_cast("I" as integer)          as profile_viewers,
    try_cast("J" as integer)          as reactions,
    try_cast("K" as integer)          as comments,
    try_cast("L" as integer)          as reposts,
    try_cast("M" as integer)          as saves,
    try_cast("N" as integer)          as sends,
    try_cast("O" as integer)          as custom_button_engagements
from {{ read_export_sheet('MOST RECENT POSTS', 'A2:O500') }}
where "A" like 'http%'
