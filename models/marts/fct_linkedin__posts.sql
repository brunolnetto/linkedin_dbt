-- Posts publicados no período do export, com seguidores ganhos na janela
-- de atribuição (dia do post + dias seguintes). Posts no mesmo dia dividem a janela.
{% set n = var('follower_attribution_days') %}
with period as (
    select min(activity_date) as start_date from {{ ref('int_linkedin__daily') }}
),

windowed as (
    select p.post_url, sum(d.new_followers) as followers_in_window
    from {{ ref('int_linkedin__posts') }} p
    join {{ ref('int_linkedin__daily') }} d
        on d.activity_date between p.published_date and p.published_date + {{ n - 1 }}
    group by p.post_url
)

select
    p.*,
    w.followers_in_window,
    count(*) over (partition by p.published_date) as posts_same_day
from {{ ref('int_linkedin__posts') }} p
cross join period
left join windowed w using (post_url)
where p.published_date >= period.start_date
