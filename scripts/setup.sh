#!/usr/bin/env bash
# Cria o ambiente Python do projeto em .venv e instala o dbt.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -x .venv/bin/dbt ]; then
  echo "Ambiente já existe em .venv. Para recriar: rm -rf .venv && make setup"
  exit 0
fi

if command -v uv >/dev/null 2>&1; then
  echo "Instalando com uv..."
  uv venv --quiet .venv
  uv pip install --quiet --python .venv/bin/python -r requirements.txt
else
  PY=$(command -v python3 || true)
  [ -n "$PY" ] || { echo "Erro: Python 3.10+ não encontrado. Instale o Python e rode de novo." >&2; exit 1; }
  "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' \
    || { echo "Erro: precisa de Python 3.10 ou mais novo (encontrado: $("$PY" --version))." >&2; exit 1; }
  echo "Instalando com pip (pode levar alguns minutos)..."
  "$PY" -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements.txt
fi

.venv/bin/python -c "import importlib.metadata as m; print('Instalado: dbt-core', m.version('dbt-core'), '+ dbt-duckdb', m.version('dbt-duckdb'))"
echo
echo "Pronto. Próximo passo: coloque seu export em exports/ e rode: make load"
