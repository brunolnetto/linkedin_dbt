"""Gera output/relatorio_linkedin.html e output/analise_llm.md a partir das tabelas do dbt.

Rode depois de carregar pelo menos um export (`make load`). Normalmente você não
chama este script direto: `make load` e `make report` já o executam.
"""
import datetime as dt
import json
import pathlib
import sys

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_prompt import PROMPT_OUTPUT, render_prompt  # noqa: E402
from insights import build_caveats, build_highlights  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "linkedin.duckdb"
TEMPLATE = ROOT / "report" / "template.html"
OUTPUT = ROOT / "output" / "relatorio_linkedin.html"

MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def load_data():
    """Lê os marts e devolve tudo o que o relatório e o prompt usam."""
    if not DB.exists():
        sys.exit("Banco não encontrado. Carregue um export primeiro: make load")

    con = duckdb.connect(str(DB), read_only=True)

    def rows(sql):
        return con.sql(sql).fetchall()

    def records(sql):
        rel = con.sql(sql)
        cols = rel.columns
        return [dict(zip(cols, r)) for r in rel.fetchall()]

    kpis = records("select * from mart_linkedin__kpis")[0]
    if not kpis["impressions"]:
        sys.exit("O histórico está vazio. Carregue um export primeiro: make load")

    weeks = [[str(w), i, e, f] for w, i, e, f in rows(
        "select week_start, impressions, engagements, new_followers from agg_linkedin__weekly order by 1")]

    posts = records("""
        select published_date::varchar as d, impressions as imp, engagements as eng,
               topic, language as lang, post_format as fmt, title_hint as title, followers_in_window as fol
        from fct_linkedin__posts order by published_date""")

    by_dim = records("select * from agg_linkedin__posts_by_dimension")
    topics = [dict(k=r["dimension_value"], n=r["posts"], imp=int(r["impressions_total"] or 0),
                   mi=r["impressions_median"], me=r["engagements_median"],
                   er=r["engagement_rate_median"], f=r["followers_in_window_median"])
              for r in by_dim if r["dimension"] == "topic"]

    months = []
    for r in records("select * from agg_linkedin__monthly order by month_start"):
        m = r["month_start"]
        label = MES[m.month - 1] + (f"/{str(m.year)[2:]}" if m.month in (1, 12) or not months else "")
        months.append(dict(label=label, n=r["posts"], i=r["impressions"], e=r["engagements"],
                           f=r["new_followers"], partial=not r["is_month_fully_covered"]))

    audience = records("""
        select dimension, dimension_value as value, followers_share as followers, content_viewers_share as viewers
        from mart_linkedin__demographics_comparison
        order by dimension, coalesce(followers_share, 0) + coalesce(content_viewers_share, 0) desc""")
    seniority = [[a["value"], a["followers"], a["viewers"]] for a in audience if a["dimension"] == "Seniority"]

    # Rótulos nos 3 maiores picos semanais: o post com mais impressões publicado na semana ou na anterior.
    annotations = []
    for wk, _ in rows("select week_start, impressions from agg_linkedin__weekly order by impressions desc limit 3"):
        top = rows(f"""
            select title_hint from fct_linkedin__posts
            where published_date between date '{wk}' - 7 and date '{wk}' + 6
            order by impressions desc nulls last limit 1""")
        if top:
            annotations.append([str(wk), top[0][0].replace("-", " ")[:40]])

    return dict(
        kpis={k: (str(v) if isinstance(v, (dt.date, dt.datetime)) else v) for k, v in kpis.items()},
        weeks=weeks, posts=posts, topics=topics, months=months, audience=audience,
        seniority=seniority, annotations=annotations,
        highlights=build_highlights(kpis, posts, months, seniority),
        caveats=build_caveats(kpis, posts, months),
        generated_at=dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


def main():
    data = load_data()
    prompt = render_prompt(data)
    PROMPT_OUTPUT.parent.mkdir(exist_ok=True)
    PROMPT_OUTPUT.write_text(prompt, encoding="utf-8")

    page = dict(data, prompt=prompt)
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*DATA*/null", json.dumps(page, ensure_ascii=False, default=str).replace("</", "<\\/"))
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Relatório gerado: {OUTPUT}")
    print(f"Prompt para IA:   {PROMPT_OUTPUT}")
    print(f"  {len(data['posts'])} posts, {len(data['weeks'])} semanas, {data['kpis']['exports_loaded']} export(s). "
          "Abra o relatório no navegador.")


if __name__ == "__main__":
    main()
