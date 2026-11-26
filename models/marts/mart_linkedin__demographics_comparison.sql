-- Seguidores x quem vê o conteúdo, na versão atual da dimensão SCD2.
-- Para ver como o público mudou, consulte dim_linkedin__audience_scd2 sem filtrar is_current.
with current_items as (
    select * from {{ ref('dim_linkedin__audience_scd2') }}
    where is_current and is_present
)
select
    dimension,
    dimension_value,
    max(share) filter (where audience = 'followers')                    as followers_share,
    max(share) filter (where audience = 'content_viewers')              as content_viewers_share,
    bool_or(is_below_1pct) filter (where audience = 'followers')        as followers_below_1pct,
    bool_or(is_below_1pct) filter (where audience = 'content_viewers')  as content_viewers_below_1pct,
    max(share) filter (where audience = 'content_viewers')
      - max(share) filter (where audience = 'followers')                as share_gap,
    max(valid_from)                                                     as as_of
from current_items
group by dimension, dimension_value
