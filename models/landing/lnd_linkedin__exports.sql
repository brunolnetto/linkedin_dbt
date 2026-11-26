{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='export_id', full_refresh=false) }}
-- Metadados de cada export carregado. A janela vem dos próprios dados diários.
select
    x.export_id,
    x.file_name,
    x.file_size_bytes,
    x.downloaded_at,
    now()                                   as loaded_at,
    d.period_start,
    d.period_end,
    d.days,
    d.daily_impressions_total,
    o.impressions                           as overview_impressions,
    o.members_reached,
    t.total_followers,
    t.snapshot_date                         as followers_snapshot_date
from {{ ref('stg_linkedin__export_file') }} x
cross join (
    select min(activity_date) as period_start, max(activity_date) as period_end,
           count(*) as days, sum(impressions) as daily_impressions_total
    from {{ ref('stg_linkedin__daily_engagement') }}
) d
cross join {{ ref('stg_linkedin__overview') }} o
cross join {{ ref('stg_linkedin__follower_total') }} t
where {{ skip_loaded_exports() }}
