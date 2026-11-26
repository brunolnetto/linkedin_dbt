{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='export_id', full_refresh=false) }}
select x.export_id, e.activity_date, e.impressions, e.engagements, coalesce(f.new_followers, 0) as new_followers
from {{ ref('stg_linkedin__daily_engagement') }} e
left join {{ ref('stg_linkedin__daily_followers') }} f using (activity_date)
cross join {{ ref('stg_linkedin__export_file') }} x
where {{ skip_loaded_exports() }}
