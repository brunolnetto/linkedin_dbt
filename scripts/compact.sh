#!/usr/bin/env bash
# Compacta linkedin.duckdb copiando tudo para um arquivo novo (recupera espaço de
# linhas apagadas que o CHECKPOINT não devolve). Mantém backup em linkedin.duckdb.bak.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f linkedin.duckdb ] || { echo "linkedin.duckdb não existe" >&2; exit 1; }
before=$(stat -c %s linkedin.duckdb)
rm -f linkedin.compact.duckdb
.venv/bin/python -I -c "
import duckdb
c = duckdb.connect()
c.execute(\"attach 'linkedin.duckdb' as src (read_only)\")
c.execute(\"attach 'linkedin.compact.duckdb' as dst\")
c.execute('copy from database src to dst')
"
mv linkedin.duckdb linkedin.duckdb.bak
mv linkedin.compact.duckdb linkedin.duckdb
after=$(stat -c %s linkedin.duckdb)
echo "Compactado: $((before/1024)) KB -> $((after/1024)) KB (backup: linkedin.duckdb.bak)"
