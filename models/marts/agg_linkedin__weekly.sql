{{ config(materialized='view') }}
select
    week_start,
    sum(impressions)   as impressions,
    sum(engagements)   as engagements,
    sum(new_followers) as new_followers,
    sum(engagements) / nullif(sum(impressions), 0) as engagement_rate
from {{ ref('int_linkedin__daily') }}
group by week_start
