-- Posts publicados no período do export, com seguidores ganhos na janela
-- de atribuição (dia do post + dias seguintes). Posts no mesmo dia dividem a janela.
-- Janela: var follower_attribution_days, ou automática (metade do intervalo
-- típico entre dias com post, entre 1 e 3 dias), para não sobrepor janelas de
-- quem publica com frequência.
with period as (
    select min(activity_date) as start_date from {{ ref('int_linkedin__daily') }}
),

post_days as (
    select distinct p.published_date
    from {{ ref('int_linkedin__posts') }} p, period
    where p.published_date >= period.start_date
),

cadence as (
    select
        {% if var('follower_attribution_days', none) %}
        {{ var('follower_attribution_days') }}::integer as window_days
        {% else %}
        coalesce(least(3, greatest(1, floor(median(gap) / 2)))::integer, 3) as window_days
        {% endif %}
    from (
        select published_date - lag(published_date) over (order by published_date) as gap
        from post_days
    )
),

windowed as (
    select p.post_url, sum(d.new_followers) as followers_in_window
    from {{ ref('int_linkedin__posts') }} p
    cross join cadence c
    join {{ ref('int_linkedin__daily') }} d
        on d.activity_date between p.published_date and p.published_date + c.window_days - 1
    group by p.post_url
)

select
    p.*,
    w.followers_in_window,
    c.window_days                                  as attribution_window_days,
    count(*) over (partition by p.published_date) as posts_same_day
from {{ ref('int_linkedin__posts') }} p
cross join period
cross join cadence c
left join windowed w using (post_url)
where p.published_date >= period.start_date
