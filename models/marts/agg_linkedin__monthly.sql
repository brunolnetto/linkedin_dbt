{{ config(materialized='view') }}
with posts as (
    select date_trunc('month', published_date)::date as month_start, count(*) as posts
    from {{ ref('fct_linkedin__posts') }}
    group by 1
)
select
    d.month_start,
    count(*)                                                    as days_with_data,
    day(last_day(d.month_start))                                as days_in_month,
    count(*) = day(last_day(d.month_start))                     as is_month_fully_covered,
    coalesce(p.posts, 0)                                        as posts,
    sum(d.impressions)                                          as impressions,
    sum(d.engagements)                                          as engagements,
    sum(d.new_followers)                                        as new_followers,
    sum(d.engagements) / nullif(sum(d.impressions), 0)          as engagement_rate,
    1000.0 * sum(d.new_followers) / nullif(sum(d.impressions), 0) as followers_per_1k_impressions
from {{ ref('int_linkedin__daily') }} d
left join posts p using (month_start)
group by d.month_start, p.posts
