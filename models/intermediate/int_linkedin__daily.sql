-- depends_on: {{ ref('stg_linkedin__export_file') }}
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='activity_date',
    on_schema_change='sync_all_columns'
) }}
-- Um registro por dia, consolidando todos os exports carregados (em qualquer ordem).
-- Quando dois exports cobrem o mesmo dia, vence:
--   1. o export em que o dia já estava completo (dia anterior à data do download);
--   2. entre esses, o baixado por último.
--
-- Incremental: numa carga, só os dias da janela do arquivo carregado são recalculados,
-- mas a escolha olha os candidatos de TODOS os exports para esses dias.
-- Sem arquivo (seletor transform), não faz nada. --full-refresh reconstrói tudo
-- a partir do histórico (landing), sem perda.
with window_to_refresh as (
    {% if is_incremental() and var('linkedin_export', none) %}
    select min(l.activity_date) as start_date, max(l.activity_date) as end_date
    from {{ ref('lnd_linkedin__daily') }} l
    where l.export_id = (select export_id from {{ ref('stg_linkedin__export_file') }})
    {% elif is_incremental() %}
    select null::date as start_date, null::date as end_date
    {% else %}
    select min(activity_date) as start_date, max(activity_date) as end_date
    from {{ ref('lnd_linkedin__daily') }}
    {% endif %}
),

candidates as (
    select
        l.*,
        x.downloaded_at,
        l.activity_date < x.downloaded_at::date as is_complete_day
    from {{ ref('lnd_linkedin__daily') }} l
    join {{ ref('lnd_linkedin__exports') }} x using (export_id)
    cross join window_to_refresh w
    where l.activity_date between w.start_date and w.end_date
),

picked as (
    select *
    from candidates
    qualify row_number() over (
        partition by activity_date
        order by is_complete_day desc, downloaded_at desc, export_id
    ) = 1
)

select
    activity_date,
    date_trunc('week', activity_date)::date   as week_start,
    date_trunc('month', activity_date)::date  as month_start,
    dayname(activity_date)                    as weekday,
    impressions,
    engagements,
    new_followers,
    is_complete_day,
    export_id                                 as source_export_id
from picked
