{{ config(materialized='view') }}
-- is_low_activity_day: dia entre os {{ var('low_activity_quantile') * 100 }}% com menos impressões
-- da própria conta (relativo, para valer em contas pequenas e grandes).
with d as (select * from {{ ref('int_linkedin__daily') }}),
threshold as (
    select quantile_cont(impressions, {{ var('low_activity_quantile') }}) as low_activity_max_impressions from d
)
select
    d.*,
    t.low_activity_max_impressions,
    d.impressions <= t.low_activity_max_impressions as is_low_activity_day,
    d.engagements / nullif(d.impressions, 0) as engagement_rate,
    avg(d.impressions) over w7               as impressions_7d_avg,
    avg(d.new_followers) over w7             as new_followers_7d_avg
from d
cross join threshold t
window w7 as (order by d.activity_date rows between 6 preceding and current row)
