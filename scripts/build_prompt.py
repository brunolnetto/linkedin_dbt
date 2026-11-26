"""Gera output/analise_llm.md: seus dados + instruções, para colar num assistente de IA.

Funciona com qualquer provedor (ChatGPT, Claude, Gemini, um modelo local...).
Nada é enviado por este script: você decide se e onde colar o arquivo.

O código calcula os números e os limites dos dados; a IA só interpreta. As
instruções pedem que ela não afirme diferenças que os dados não sustentam.

Uso: make prompt   (make load e make report também geram o arquivo)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from insights import FEW_POSTS_PER_GROUP, MIN_POSTS_PER_GROUP, MIN_RELATIVE_DIFF  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPT_OUTPUT = ROOT / "output" / "analise_llm.md"

MAX_POSTS = 200        # posts listados no prompt (os mais recentes)
MAX_AUDIENCE_ROWS = 8  # linhas por dimensão do público


def _cell(v, kind=None):
    if v is None:
        return "–"
    if kind == "pct":
        return f"{100 * v:.1f}%"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else f"{v:.2f}"
    return str(v).replace("|", "/")


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def render_prompt(data):
    k = data["kpis"]
    posts = data["posts"][-MAX_POSTS:]
    s = []

    s.append(f"""# Análise do meu LinkedIn

Você é um analista de dados ajudando um profissional a entender o desempenho dele no LinkedIn.
Abaixo estão os dados exportados do LinkedIn, já consolidados e calculados por código. Use os
números como estão; não invente métricas que não estão aqui.

## Regras para a sua análise

1. **Comece perguntando o meu objetivo** (ex.: ganhar seguidores, ser encontrado por recrutadores,
   gerar clientes, construir autoridade num tema) e só recomende algo depois da resposta.
2. **Toda comparação pode ter três respostas:** A maior que B, B maior que A, ou sem diferença clara.
   Trate como "sem diferença clara" grupos com menos de {MIN_POSTS_PER_GROUP} posts ou diferenças menores que
   {int(MIN_RELATIVE_DIFF * 100)}% entre medianas. Com menos de {FEW_POSTS_PER_GROUP} posts por grupo, chame de hipótese, não de conclusão.
3. **Cite os números** (valor e quantidade de posts) em cada afirmação.
4. **Respeite os limites dos dados** listados abaixo. Não tire conclusões que eles impedem.
5. **Correlação não é causa.** Proponha testes (ex.: "publique 4 posts do tipo X em 4 semanas e compare")
   em vez de afirmar o que causa o quê.
6. Os títulos vêm da URL do post (sem acentos, cortados). Agrupe os posts por tema a partir deles se
   isso ajudar; diga quais posts ficaram em cada grupo.

## O que eu quero saber

- O que funcionou e o que não funcionou, com evidência.
- Quais padrões são fortes e quais podem ser acaso.
- O que os dados ainda não permitem saber e o que eu precisaria medir.
- 3 experimentos concretos para os próximos 3 meses, cada um com como medir o resultado.

## Período e totais

Período: {k['coverage_start']} a {k['coverage_end']} ({k['days_covered']} dias, {k['exports_loaded']} export(s) do LinkedIn).
""")
    s.append(table(["Indicador", "Valor"], [
        ["Impressões", _cell(k["impressions"])],
        ["Engajamentos", _cell(k["engagements"])],
        ["Taxa de engajamento", _cell(k["engagement_rate"], "pct")],
        ["Novos seguidores no período", _cell(k["new_followers"])],
        ["Seguidores totais", f"{_cell(k['total_followers'])} (em {k['total_followers_as_of']})"],
        ["Posts com métricas", _cell(k["posts"])],
        ["Impressões num dia típico (mediana)", _cell(k["daily_impressions_median"])],
        ["Fatia das impressões nos 10% melhores dias", _cell(k["top10pct_days_share"], "pct")],
        ["Correlação diária novos seguidores × engajamentos", _cell(k["corr_followers_engagements"])],
        ["Correlação diária novos seguidores × impressões", _cell(k["corr_followers_impressions"])],
        ["Correlação seguidores do dia seguinte × engajamentos", _cell(k["corr_next_day_followers_engagements"])],
        [f"Seguidores/dia nos {k['low_activity_days']} dias de menor alcance (até {_cell(k['low_activity_max_impressions'])} impr.)",
         _cell(k["baseline_followers_per_day"])],
    ]))

    s.append("\n## Limites dos dados\n")
    s += [f"- {c}" for c in data["caveats"]]

    s.append("\n## Frases já calculadas pelo código\n")
    s.append("Seguem as regras acima. Se discordar de alguma, mostre o cálculo.\n")
    s += [f"- {h}" for h in data["highlights"]]

    s.append("\n## Por mês\n")
    s.append(table(["Mês", "Posts", "Impressões", "Engajamentos", "Novos seguidores", "Mês completo"], [
        [m["label"], _cell(m["n"]), _cell(m["i"]), _cell(m["e"]), _cell(m["f"]), "não" if m["partial"] else "sim"]
        for m in data["months"]]))

    s.append("\n## Por semana (início na segunda-feira)\n")
    s.append(table(["Semana", "Impressões", "Engajamentos", "Novos seguidores"],
                   [[w[0], _cell(w[1]), _cell(w[2]), _cell(w[3])] for w in data["weeks"]]))

    s.append(f"\n## Posts ({len(posts)})\n")
    s.append("Seguidores na janela: novos seguidores do dia do post e seguintes (aproximação). "
             "Tema e idioma vêm de regras simples pela URL e podem estar errados.\n")
    s.append(table(["Data", "Título (da URL)", "Impressões", "Engajamentos", "Taxa", "Idioma", "Formato", "Tema",
                    "Seguidores na janela"], [
        [p["d"], _cell(p["title"].replace("-", " ")[:80]), _cell(p["imp"]), _cell(p["eng"]),
         _cell(p["eng"] / p["imp"], "pct") if p["imp"] and p["eng"] is not None else "–",
         _cell(p["lang"]), _cell(p["fmt"]), _cell(p["topic"]), _cell(p["fol"])]
        for p in posts]))

    if data["audience"]:
        s.append("\n## Público: seguidores × quem vê o conteúdo\n")
        s.append("Percentual de cada grupo. \"–\" = abaixo de 1% ou fora da lista do LinkedIn.\n")
        dims = {}
        for a in data["audience"]:
            dims.setdefault(a["dimension"], []).append(a)
        for dim, items in dims.items():
            s.append(f"\n### {dim}\n")
            s.append(table(["Valor", "Seguidores", "Quem vê o conteúdo"], [
                [_cell(a["value"]), _cell(a["followers"], "pct"), _cell(a["viewers"], "pct")]
                for a in items[:MAX_AUDIENCE_ROWS]]))

    return "\n".join(s) + "\n"


def main():
    from build_report import load_data
    PROMPT_OUTPUT.parent.mkdir(exist_ok=True)
    PROMPT_OUTPUT.write_text(render_prompt(load_data()), encoding="utf-8")
    print(f"Prompt gerado: {PROMPT_OUTPUT}")
    print("Ele contém os títulos dos seus posts e o perfil do seu público. Você decide se e onde colar.")


if __name__ == "__main__":
    main()
