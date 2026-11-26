-- Métricas de post no export são do período do export, não da vida toda do post.
-- Entre vários exports, fica o maior valor visto (o export que cobriu mais da vida do post).
with top_per_export as (
    select
        export_id,
        post_url,
        any_value(published_date)                                          as published_date,
        max(case when ranking_metric = 'impressions' then metric_value end) as impressions,
        max(case when ranking_metric = 'engagements' then metric_value end) as engagements
    from {{ ref('lnd_linkedin__top_posts') }}
    group by export_id, post_url
),

ranked as (
    select
        post_url,
        any_value(published_date)        as published_date,
        max(impressions)                 as impressions,
        max(engagements)                 as engagements,
        bool_or(impressions is not null) as in_top_impressions,
        bool_or(engagements is not null) as in_top_engagements,
        count(distinct export_id)        as exports_seen
    from top_per_export
    group by post_url
),

recent as (
    -- Para posts recentes, usa a leitura do export baixado por último.
    select r.*, r.reactions + r.comments + r.reposts + r.saves + r.sends as engagements_calc
    from {{ ref('lnd_linkedin__recent_posts') }} r
    join {{ ref('lnd_linkedin__exports') }} x using (export_id)
    qualify row_number() over (partition by r.post_url order by x.downloaded_at desc) = 1
),

posts as (
    select
        coalesce(r.post_url, n.post_url)                       as post_url,
        coalesce(r.published_date, n.published_date)           as published_date,
        greatest(r.impressions, n.impressions)                 as impressions,
        coalesce(greatest(r.engagements, n.engagements_calc), r.engagements, n.engagements_calc) as engagements,
        n.post_type, n.members_reached, n.followers_gained, n.pct_out_of_network,
        coalesce(r.in_top_impressions, false)                  as in_top_impressions,
        coalesce(r.in_top_engagements, false)                  as in_top_engagements,
        n.post_url is not null                                 as in_recent_posts
    from ranked r
    full outer join recent n on r.post_url = n.post_url
),

parsed as (
    select
        *,
        regexp_extract(post_url, '(?:share|ugcPost)-(\d{10,})', 1)           as post_id,
        url_decode(regexp_extract(post_url, '/posts/[^_]+_(.*)$', 1))    as slug,
        case when post_url like '%ugcPost%' then 'documento/mídia' else 'texto/link' end as post_format
    from posts
),

topic as (
    select p.post_url, arg_min(t.topic, t.priority) as topic
    from parsed p
    join {{ ref('topic_rules') }} t on contains(p.slug, t.pattern)
    group by p.post_url
),

lang as (
    select p.post_url, arg_min(l.language, l.priority) as language
    from parsed p
    join {{ ref('language_rules') }} l on contains(p.slug, l.pattern)
    group by p.post_url
)

select
    p.post_id,
    p.post_url,
    p.slug,
    regexp_replace(p.slug, '-(share|ugcPost)-\d{10,}-.*$', '')  as title_hint,
    p.published_date,
    dayname(p.published_date)                               as published_weekday,
    p.post_format,
    coalesce(t.topic, 'Outros')                             as topic,
    coalesce(l.language, 'EN')                              as language,
    p.impressions,
    p.engagements,
    p.engagements / nullif(p.impressions, 0)                as engagement_rate,
    p.post_type, p.members_reached, p.followers_gained, p.pct_out_of_network,
    p.in_top_impressions, p.in_top_engagements, p.in_recent_posts
from parsed p
left join topic t using (post_url)
left join lang l using (post_url)
