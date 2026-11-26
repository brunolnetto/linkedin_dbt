#!/usr/bin/env bash
# Carrega exports do LinkedIn no histórico e gera o relatório.
#
#   scripts/ingest.sh                       # carrega todos os .xlsx de exports/
#   scripts/ingest.sh caminho/export.xlsx   # carrega arquivos específicos
#
# Pode rodar quantas vezes quiser: arquivos já carregados são ignorados.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -x .venv/bin/dbt ] || { echo "Ambiente não instalado. Rode primeiro: make setup" >&2; exit 1; }

if [ $# -eq 0 ]; then
  shopt -s nullglob
  set -- exports/*.xlsx
  [ $# -gt 0 ] || { echo "Nenhum .xlsx em exports/. Baixe seu export do LinkedIn e coloque lá (veja o README)." >&2; exit 1; }
fi

total=$#; n=0
for f in "$@"; do
  n=$((n + 1))
  [ -f "$f" ] || { echo "Arquivo não encontrado: $f" >&2; exit 1; }
  file="$(realpath "$f")"
  echo "[$n/$total] Carregando $(basename "$file")..."
  vars=$(.venv/bin/python -c 'import json,sys; print(json.dumps({"linkedin_export": sys.argv[1]}))' "$file")
  if ! .venv/bin/dbt --quiet build --profiles-dir . --selector ingest --vars "$vars"; then
    echo >&2
    echo "Falhou ao carregar $(basename "$file"). Detalhes acima e em logs/dbt.log." >&2
    echo "Se for um export do LinkedIn, rodar de novo é seguro. Veja 'Problemas comuns' no README." >&2
    exit 1
  fi
done

echo
.venv/bin/python -I scripts/build_report.py
.venv/bin/python -I - <<'PY'
import duckdb
c = duckdb.connect('linkedin.duckdb', read_only=True)
print('\nExports no histórico:')
for name, dl, a, b in c.sql("""select regexp_extract(file_name, '[^/]+$'), downloaded_at::date, period_start, period_end
                                from lnd_linkedin__exports order by period_start, downloaded_at""").fetchall():
    print(f'  {a} a {b}  (baixado em {dl})  {name}')
s, e, days, gap = c.sql("select coverage_start, coverage_end, days_covered, days_missing_in_coverage from mart_linkedin__kpis").fetchall()[0]
print(f'Cobertura: {s} a {e}, {days} dias' + (f' ({gap} dias faltando no meio)' if gap else ''))
PY
