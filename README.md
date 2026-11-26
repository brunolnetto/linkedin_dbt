# LinkedIn em dados

Transforme o export de analytics do LinkedIn num relatório que mostra o que traz alcance, conversa e
seguidores. Feito com [dbt](https://www.getdbt.com/) e [DuckDB](https://duckdb.org/): roda no seu
computador, sem banco de dados para instalar e sem enviar seus dados para lugar nenhum.

O relatório traz:

- impressões, engajamento e novos seguidores por semana e por mês;
- cada post num gráfico de impressões × engajamentos, por idioma;
- desempenho por tema (você define os temas);
- quem te segue × quem lê seu conteúdo (senioridade);
- frases automáticas com os principais padrões, geradas a partir dos números.

## Antes de começar

Você precisa de:

- **Linux, macOS ou Windows com [WSL](https://learn.microsoft.com/pt-br/windows/wsl/install)**;
- **Python 3.10 ou mais novo** (`python3 --version` para conferir);
- **make** (já vem no Linux e no macOS; no Ubuntu/WSL: `sudo apt install make`).

Não precisa saber dbt nem SQL para usar.

## Passo a passo

### 1. Instale

```bash
git clone <url-deste-repositório>
cd linkedin_dbt
make setup
```

Isso cria um ambiente isolado em `.venv/` e instala o dbt. Leva de 1 a 5 minutos e só precisa ser feito uma vez.

### 2. Baixe seu export do LinkedIn

1. No LinkedIn, abra seu perfil e vá em **Analytics** (ou "Análises") → **Impressões de publicações**.
2. Escolha o período (até 365 dias) e clique em **Exportar**.
3. Você recebe um arquivo `.xlsx`, algo como `AggregateAnalytics_Seu_Nome_2025-01-01_2025-12-31.xlsx`.

O LinkedIn muda os menus de vez em quando; se não achar, procure por "exportar analytics" na ajuda dele.

### 3. Carregue e gere o relatório

Coloque o `.xlsx` na pasta `exports/` e rode:

```bash
make load
```

Abra `output/relatorio_linkedin.html` no navegador.

## Atualizando com novos exports

Baixe um export novo quando quiser, coloque em `exports/` e rode `make load` de novo.

- **Os dados se acumulam.** Cada export soma ao histórico. Dá para juntar vários anos.
- **Qualquer período, qualquer ordem.** Pode baixar janelas que se sobrepõem, ou um período antigo
  depois de um recente. Quando dois exports cobrem o mesmo dia, o projeto escolhe o dado mais completo.
- **Rodar de novo é seguro.** Arquivos já carregados são ignorados; nada duplica.
- **Guarde os `.xlsx`.** O histórico fica em `linkedin.duckdb`, mas com os arquivos você sempre consegue reconstruí-lo.

## Comandos

| Comando | O que faz |
|---|---|
| `make setup` | Instala o dbt (uma vez) |
| `make load` | Carrega os exports de `exports/` e gera o relatório |
| `make load FILE=caminho/export.xlsx` | Carrega um arquivo de outro lugar |
| `make report` | Gera o relatório de novo sem ler os `.xlsx` (ex.: depois de editar os temas) |
| `make test` | Confere a integridade dos dados |
| `make docs` | Abre a documentação de todas as tabelas no navegador |
| `make compact` | Reduz o tamanho do banco |
| `make reset CONFIRM=sim` | Apaga o histórico para começar do zero (os `.xlsx` ficam) |

## Personalizando os temas

O LinkedIn não diz o assunto de cada post. O projeto deduz o tema pela URL do post, que contém as
primeiras palavras e as hashtags. As regras ficam em [`seeds/topic_rules.csv`](seeds/topic_rules.csv):

```csv
priority,pattern,topic
1,jobsearch,Carreira
3,dataengineering,Engenharia de dados
```

Se a URL contém `pattern`, o post recebe `topic`. Se várias regras batem, vence a de menor `priority`.
Posts sem regra ficam como "Outros". Edite o arquivo e rode `make report`.

O idioma funciona igual, em [`seeds/language_rules.csv`](seeds/language_rules.csv); sem regra, o post é
considerado em inglês.

Dica: para ver as URLs dos seus posts, abra a aba `TOP POSTS` do seu `.xlsx`.

## Seus dados ficam com você

- Tudo roda localmente. Nada é enviado para serviços externos.
- O `.gitignore` impede que `exports/`, `output/` e o banco `linkedin.duckdb` entrem no git.
  Se fizer um fork, seus dados não vão junto.
- O relatório carrega fontes do Google Fonts ao ser aberto; os dados ficam dentro do próprio arquivo.

## Problemas comuns

**`Ambiente não instalado. Rode primeiro: make setup`**
Rode `make setup` dentro da pasta do projeto.

**`Nenhum .xlsx em exports/`**
Coloque o arquivo baixado do LinkedIn dentro da pasta `exports/` (não em subpastas).

**Falha no teste `assert_export_daily_matches_overview`**
O total de impressões do arquivo não bate com a soma dos dias. Normalmente significa que o LinkedIn
mudou o formato da planilha. Abra uma issue com os nomes das abas e as primeiras linhas de cada uma
(sem seus dados).

**O relatório diz que há poucos dados**
As frases automáticas precisam de pelo menos 30 dias e alguns posts por tema. Carregue um período maior.

**Quero abrir o banco no DBeaver ou no `duckdb` da linha de comando**
Use um cliente com DuckDB 2.x. Versões anteriores não abrem o arquivo.

## Como funciona por dentro

Veja [docs/ARQUITETURA.md](docs/ARQUITETURA.md): camadas do dbt, carga incremental, como exports
sobrepostos são combinados, dimensões SCD2 e testes.

```
exports/     seus .xlsx (fora do git)
output/      relatório gerado (fora do git)
models/      transformações dbt: staging → landing → intermediate → marts
seeds/       regras de tema e idioma (edite à vontade)
snapshots/   histórico da classificação dos posts
report/      modelo do relatório HTML
scripts/     instalação, carga, relatório e compactação
```
