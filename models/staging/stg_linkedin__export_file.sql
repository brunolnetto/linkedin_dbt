-- Identidade do arquivo apontado em var('linkedin_export').
-- export_id = md5 do conteúdo: carregar o mesmo arquivo de novo não duplica nada.
-- downloaded_at = data de modificação do arquivo (momento do download no navegador).
{% if execute and not var('linkedin_export', none) %}
    {{ exceptions.raise_compiler_error(
        "Nenhum arquivo informado. Use scripts/ingest.sh <arquivo.xlsx> "
        ~ "ou --selector ingest --vars '{linkedin_export: ...}'") }}
{% endif %}
select
    md5(content)                as export_id,
    filename                    as file_name,
    size                        as file_size_bytes,
    last_modified               as downloaded_at
from read_blob('{{ var("linkedin_export") }}')
