"""Gera output/relatorio_linkedin.html a partir das tabelas do dbt.

Rode depois de carregar pelo menos um export (`make load`). Normalmente você não
chama este script direto: `make load` e `make report` já o executam.
"""
import datetime as dt
import json
import pathlib
import sys

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "linkedin.duckdb"
TEMPLATE = ROOT / "report" / "template.html"
OUTPUT = ROOT / "output" / "relatorio_linkedin.html"

MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MIN_POSTS_PER_GROUP = 3  # grupos menores que isso não entram nas frases automáticas


def pct(v, d=1):
    return f"{100 * v:.{d}f}%".replace(".", ",")


def num(v):
    return f"{v:,.0f}".replace(",", ".")


def dec(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def main():
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
               topic, language as lang, title_hint as title, followers_in_window as fol
        from fct_linkedin__posts order by published_date""")

    by_dim = records("select * from agg_linkedin__posts_by_dimension")
    topics = [dict(k=r["dimension_value"], n=r["posts"], imp=int(r["impressions_total"] or 0),
                   mi=r["impressions_median"], me=r["engagements_median"],
                   er=r["engagement_rate_median"], f=r["followers_in_window_median"])
              for r in by_dim if r["dimension"] == "topic"]
    langs = [r for r in by_dim if r["dimension"] == "language"]

    months = []
    for r in records("select * from agg_linkedin__monthly order by month_start"):
        m = r["month_start"]
        label = MES[m.month - 1] + (f"/{str(m.year)[2:]}" if m.month in (1, 12) or not months else "")
        months.append(dict(label=label, n=r["posts"], i=r["impressions"], e=r["engagements"],
                           f=r["new_followers"], partial=not r["is_month_fully_covered"]))

    seniority = [[v, f, c] for v, f, c in rows("""
        select dimension_value, followers_share, content_viewers_share
        from mart_linkedin__demographics_comparison
        where dimension = 'Seniority'
        order by coalesce(followers_share, 0) + coalesce(content_viewers_share, 0) desc""")]

    # Rótulos nos 3 maiores picos semanais: o post com mais impressões publicado na semana ou na anterior.
    annotations = []
    for wk, _ in rows("select week_start, impressions from agg_linkedin__weekly order by impressions desc limit 3"):
        top = rows(f"""
            select title_hint from fct_linkedin__posts
            where published_date between date '{wk}' - 7 and date '{wk}' + 6
            order by impressions desc nulls last limit 1""")
        if top:
            annotations.append([str(wk), top[0][0].replace("-", " ")[:40]])

    highlights = build_highlights(kpis, topics, langs, months, seniority)

    data = dict(kpis={k: (str(v) if isinstance(v, (dt.date, dt.datetime)) else v) for k, v in kpis.items()},
                weeks=weeks, posts=posts, topics=topics, months=months, seniority=seniority,
                annotations=annotations, highlights=highlights,
                generated_at=dt.datetime.now().strftime("%d/%m/%Y %H:%M"))

    html = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(data, ensure_ascii=False, default=str))
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Relatório gerado: {OUTPUT}")
    print(f"  {len(posts)} posts, {len(weeks)} semanas, {kpis['exports_loaded']} export(s). Abra o arquivo no navegador.")


def build_highlights(k, topics, langs, months, seniority):
    """Frases curtas e verificáveis. Cada uma só aparece quando há dados suficientes."""
    out = []

    if k["days_covered"] >= 30:
        out.append(f"Seu alcance é concentrado: os 10 melhores dias somaram {pct(k['top10_days_share'], 0)} "
                   f"das impressões, enquanto um dia típico teve {num(k['daily_impressions_median'])}.")

    ce, ci = k["corr_followers_engagements"], k["corr_followers_impressions"]
    if ce is not None and ci is not None and k["days_covered"] >= 30:
        if ce > ci + 0.1:
            out.append(f"Novos seguidores acompanham mais os engajamentos (correlação {dec(ce, 2)}) do que as "
                       f"impressões ({dec(ci, 2)}): posts que geram conversa tendem a trazer mais seguidores que posts só vistos.")
        elif ci > ce + 0.1:
            out.append(f"Novos seguidores acompanham mais as impressões (correlação {dec(ci, 2)}) do que os "
                       f"engajamentos ({dec(ce, 2)}): alcance tem pesado mais que conversa.")

    if k["low_activity_days"] >= 14 and k["baseline_share_of_followers"]:
        out.append(f"Mesmo em dias quase sem impressões você ganhou em média {dec(k['baseline_followers_per_day'])} "
                   f"seguidor(es) por dia. Isso sugere que cerca de {pct(k['baseline_share_of_followers'], 0)} do "
                   f"crescimento vem do perfil e de buscas, não dos posts.")

    big = [t for t in topics if t["n"] >= MIN_POSTS_PER_GROUP and t["er"] is not None]
    if len(big) >= 2:
        best = max(big, key=lambda t: t["er"])
        reach = max(big, key=lambda t: t["mi"] or 0)
        out.append(f"Entre temas com {MIN_POSTS_PER_GROUP}+ posts, \"{best['k']}\" teve a maior taxa de engajamento "
                   f"mediana ({pct(best['er'])}, {best['n']} posts).")
        if reach["k"] != best["k"]:
            out.append(f"\"{reach['k']}\" teve o maior alcance mediano ({num(reach['mi'])} impressões por post), "
                       f"mas engajamento de {pct(reach['er'])}.")

    lg = sorted([l for l in langs if l["posts"] >= MIN_POSTS_PER_GROUP], key=lambda l: -l["posts"])
    if len(lg) >= 2:
        a, b = lg[0], lg[1]
        out.append(f"Por idioma: {a['dimension_value']} ({a['posts']} posts) teve mediana de "
                   f"{dec(a['engagements_median'], 0)} engajamentos por post; {b['dimension_value']} "
                   f"({b['posts']} posts), {dec(b['engagements_median'], 0)}.")

    full = [m for m in months if not m["partial"]]
    with_posts = [m for m in full if m["n"] > 0]
    without = [m for m in full if m["n"] == 0]
    if with_posts and without:
        avg_w = sum(m["i"] for m in with_posts) / len(with_posts)
        avg_wo = sum(m["i"] for m in without) / len(without)
        out.append(f"Meses sem nenhum post ({len(without)}) tiveram em média {num(avg_wo)} impressões, "
                   f"contra {num(avg_w)} nos meses com posts.")
    if len(full) >= 3:
        best_m = max(full, key=lambda m: m["f"])
        out.append(f"O melhor mês em seguidores foi {best_m['label']}, com {best_m['f']} novos seguidores "
                   f"e {best_m['n']} posts.")

    s = {v: (f, c) for v, f, c in seniority}
    if "Entry" in s and "Senior" in s and all(x is not None for x in s["Entry"] + s["Senior"]):
        (ef, ec), (sf, sc) = s["Entry"], s["Senior"]
        out.append(f"Entre seus seguidores, {pct(sf, 0)} são Senior e {pct(ef, 0)} Entry; entre quem vê seu "
                   f"conteúdo, {pct(sc, 0)} e {pct(ec, 0)}.")

    if not out:
        out.append("Ainda há poucos dados para destaques automáticos. Carregue um export com pelo menos 30 dias.")
    return out


if __name__ == "__main__":
    main()
