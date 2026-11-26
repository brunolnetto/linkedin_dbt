-- SCD tipo 2 do perfil do público (seguidores e quem vê o conteúdo).
-- Uma versão por período em que o percentual de um item ficou igual.
--
-- Por que não `dbt snapshot`: o snapshot marca validade pelo horário da execução e
-- supõe dados chegando em ordem. Aqui um export antigo pode ser carregado depois de um
-- novo. Montando as versões a partir do histórico (lnd_*), ordenadas pela data do
-- download, o resultado é o mesmo em qualquer ordem de carga e pode ser reconstruído.
--
-- is_present = false: o item saiu da lista do LinkedIn (ex.: empresa caiu do top 10).
with exports as (
    select export_id, downloaded_at
    from {{ ref('lnd_linkedin__exports') }}
    where export_id in (select export_id from {{ ref('lnd_linkedin__demographics') }})
),

keys as (
    select distinct audience, dimension, dimension_value
    from {{ ref('lnd_linkedin__demographics') }}
),

observations as (
    select
        k.audience, k.dimension, k.dimension_value,
        e.export_id, e.downloaded_at,
        d.share, d.share_label,
        coalesce(d.is_below_1pct, false)   as is_below_1pct,
        d.export_id is not null            as is_present
    from keys k
    cross join exports e
    left join {{ ref('lnd_linkedin__demographics') }} d
        on  d.export_id = e.export_id
        and d.audience = k.audience
        and d.dimension = k.dimension
        and d.dimension_value = k.dimension_value
),

flagged as (
    select
        *,
        case
            when lag(is_present) over w is null then 1
            when lag(is_present) over w <> is_present then 1
            when lag(share_label) over w is distinct from share_label then 1
            else 0
        end as is_new_version
    from observations
    window w as (partition by audience, dimension, dimension_value order by downloaded_at, export_id)
),

versioned as (
    select
        *,
        sum(is_new_version) over (
            partition by audience, dimension, dimension_value
            order by downloaded_at, export_id
            rows unbounded preceding
        ) as version
    from flagged
),

collapsed as (
    select
        audience, dimension, dimension_value, version,
        any_value(share)          as share,
        any_value(share_label)    as share_label,
        any_value(is_below_1pct)  as is_below_1pct,
        any_value(is_present)     as is_present,
        min(downloaded_at)        as valid_from,
        arg_min(export_id, downloaded_at) as first_export_id,
        count(*)                  as exports_in_version
    from versioned
    group by audience, dimension, dimension_value, version
),

final as (
    select
        *,
        lead(valid_from) over (partition by audience, dimension, dimension_value order by version) as valid_to
    from collapsed
)

select
    md5(concat_ws('|', audience, dimension, dimension_value))                as audience_item_key,
    md5(concat_ws('|', audience, dimension, dimension_value, valid_from))    as scd_id,
    audience,
    dimension,
    dimension_value,
    version,
    share,
    share_label,
    is_below_1pct,
    is_present,
    valid_from,
    valid_to,
    valid_to is null                                                          as is_current,
    first_export_id,
    exports_in_version
from final
