{{ config(materialized='view') }}
select
    *,
    engagements / nullif(impressions, 0) as engagement_rate,
    avg(impressions) over w7             as impressions_7d_avg,
    avg(new_followers) over w7           as new_followers_7d_avg
from {{ ref('int_linkedin__daily') }}
window w7 as (order by activity_date rows between 6 preceding and current row)
