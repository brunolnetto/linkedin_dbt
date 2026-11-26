-- Em cada export, a soma diária de impressões deve bater com o total da aba DISCOVERY.
-- Falhar aqui costuma indicar mudança no layout da planilha do LinkedIn.
select export_id, file_name, overview_impressions, daily_impressions_total
from {{ ref('lnd_linkedin__exports') }}
where overview_impressions <> daily_impressions_total
