-- Cada item do público deve ter exatamente uma versão atual, e as versões não podem se sobrepor.
select audience, dimension, dimension_value, count(*) filter (where is_current) as current_versions
from {{ ref('dim_linkedin__audience_scd2') }}
group by all
having count(*) filter (where is_current) <> 1
union all
select a.audience, a.dimension, a.dimension_value, -1
from {{ ref('dim_linkedin__audience_scd2') }} a
join {{ ref('dim_linkedin__audience_scd2') }} b
  on a.audience_item_key = b.audience_item_key and a.scd_id <> b.scd_id
 and a.valid_from < coalesce(b.valid_to, 'infinity'::timestamptz)
 and b.valid_from < coalesce(a.valid_to, 'infinity'::timestamptz)
