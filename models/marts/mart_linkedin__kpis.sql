-- Indicadores de todo o histórico carregado, numa linha.
-- members_reached não existe aqui: alcance único não pode ser somado entre exports (fica em lnd_linkedin__exports).
with d as (select * from {{ ref('fct_linkedin__daily') }}),
latest_export as (
    select * from {{ ref('lnd_linkedin__exports') }} order by downloaded_at desc limit 1
),
lagged as (
    select *, lead(new_followers) over (order by activity_date) as next_day_followers from d
),
ranked as (
    select impressions, row_number() over (order by impressions desc) as rn, count(*) over () as n_days from d
),
post_lists as (
    -- Linhas por ranking (impressões / engajamentos) em cada export.
    select export_id, ranking_metric, count(*) as list_rows
    from {{ ref('lnd_linkedin__top_posts') }}
    group by all
)
select
    (select sum(impressions) from d)                                     as impressions,
    (select sum(engagements) from d)                                     as engagements,
    (select sum(new_followers) from d)                                   as new_followers,
    (select total_followers from latest_export)                         as total_followers,
    (select followers_snapshot_date from latest_export)                 as total_followers_as_of,
    (select count(*) from {{ ref('lnd_linkedin__exports') }})           as exports_loaded,
    (select min(activity_date) from d)                                  as coverage_start,
    (select max(activity_date) from d)                                  as coverage_end,
    (select count(*) from d)                                            as days_covered,
    (select max(activity_date) - min(activity_date) + 1 - count(*) from d) as days_missing_in_coverage,
    (select count(*) from {{ ref('fct_linkedin__posts') }})              as posts,
    (select max(attribution_window_days) from {{ ref('fct_linkedin__posts') }}) as attribution_window_days,
    (select max(list_rows) from post_lists)                             as top_posts_list_max_rows,
    coalesce((select max(list_rows) from post_lists) >= {{ var('top_posts_list_limit') }}, false)
                                                                          as top_posts_list_truncated,
    (select sum(engagements) / sum(impressions) from d)                  as engagement_rate,
    (select median(impressions) from d)                                  as daily_impressions_median,
    (select sum(impressions) filter (where rn <= 10) / sum(impressions) from ranked)              as top10_days_share,
    (select sum(impressions) filter (where rn <= ceil(n_days * 0.1)) / sum(impressions) from ranked) as top10pct_days_share,
    (select max(low_activity_max_impressions) from d)                     as low_activity_max_impressions,
    (select avg(new_followers) filter (where is_low_activity_day) from d) as baseline_followers_per_day,
    (select count(*) filter (where is_low_activity_day) from d)           as low_activity_days,
    (select least(1, avg(new_followers) filter (where is_low_activity_day) * count(*) / nullif(sum(new_followers), 0)) from d)
                                                                          as baseline_share_of_followers,
    (select corr(engagements, new_followers) from d)                      as corr_followers_engagements,
    (select corr(impressions, new_followers) from d)                      as corr_followers_impressions,
    (select corr(engagements, next_day_followers) from lagged)            as corr_next_day_followers_engagements
