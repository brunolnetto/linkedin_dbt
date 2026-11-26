# Atalhos do projeto. Rode `make` para ver a lista.
.DEFAULT_GOAL := help
DBT := .venv/bin/dbt
PY  := .venv/bin/python
export DBT_PROFILES_DIR := .

.PHONY: help setup load report prompt test docs compact clean reset

help: ## Mostra esta ajuda
	@echo "Uso: make <comando>"
	@echo
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-9s %s\n", $$1, $$2}'

setup: ## Instala o dbt num ambiente isolado (.venv). Rode uma vez.
	@scripts/setup.sh

load: ## Carrega os exports de exports/ e gera o relatório. Ou: make load FILE=caminho.xlsx
	@scripts/ingest.sh $(if $(FILE),"$(FILE)")

report: ## Recalcula tudo a partir do histórico (sem ler xlsx) e gera o relatório
	@$(DBT) --quiet build
	@$(PY) -I scripts/build_report.py

prompt: ## Gera output/analise_llm.md para colar no assistente de IA que preferir
	@$(PY) -I scripts/build_prompt.py

test: ## Roda os testes de dados e os unit tests
	@$(DBT) test

docs: ## Abre a documentação do dbt (modelos, colunas e linhagem) no navegador
	@$(DBT) docs generate --quiet && $(DBT) docs serve

compact: ## Reduz o tamanho do banco linkedin.duckdb
	@scripts/compact.sh

clean: ## Apaga arquivos temporários do dbt (target/, logs/)
	@$(DBT) clean --quiet

reset: ## Apaga o histórico (linkedin.duckdb). Peça com: make reset CONFIRM=sim
	@if [ "$(CONFIRM)" != "sim" ]; then \
	  echo "Isso apaga todo o histórico carregado. Os .xlsx em exports/ não são apagados."; \
	  echo "Para confirmar: make reset CONFIRM=sim"; exit 1; fi
	@rm -f linkedin.duckdb linkedin.duckdb.wal linkedin.duckdb.bak output/relatorio_linkedin.html
	@echo "Histórico apagado. Recarregue com: make load"
