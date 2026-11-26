-- Só os atributos descritivos do post, para o snapshot SCD2 de classificação.
select post_url, post_id, slug, topic, language, post_format
from {{ ref('int_linkedin__posts') }}
