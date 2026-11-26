{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='export_id', full_refresh=false) }}
select x.export_id, s.*
from {{ ref('stg_linkedin__demographics') }} s
cross join {{ ref('stg_linkedin__export_file') }} x
where {{ skip_loaded_exports() }}
