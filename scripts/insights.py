"""Frases automáticas do relatório, sem pressupor o resultado.

Regras que valem para qualquer conta:
- Toda pergunta tem resposta nos dois sentidos e também "sem diferença clara".
- Uma diferença só vira conclusão com grupos de pelo menos MIN_POSTS_PER_GROUP posts
  e diferença relativa de pelo menos MIN_RELATIVE_DIFF.
- Limitações detectadas nos dados (listas truncadas, meses parciais, dias faltando)
  viram avisos e suprimem frases que dependem delas.

Funções puras, sem banco: recebem dicionários e devolvem listas de frases.
Testadas em tests_py/test_insights.py com contas simuladas.
"""
from statistics import median

MIN_DAYS = 30               # menos que isso: sem frases sobre a série diária
MIN_POSTS_PER_GROUP = 5     # grupos menores não entram nas comparações
FEW_POSTS_PER_GROUP = 10    # abaixo disso, a frase avisa que é hipótese
MIN_RELATIVE_DIFF = 0.30    # diferença mínima entre medianas para afirmar algo
MIN_CORR = 0.20             # correlação abaixo disso conta como "quase nenhuma"
MIN_CORR_DIFF = 0.10        # diferença mínima entre duas correlações
MIN_MONTHS_PER_SIDE = 2     # meses com e sem post necessários para comparar
MIN_PP_GAP = 0.05           # diferença mínima (pontos percentuais) entre públicos

DIMENSIONS = [("topic", "tema"), ("lang", "idioma"), ("fmt", "formato")]
METRICS = [("imp", "impressões por post"), ("er", "taxa de engajamento")]
OTHER_TOPIC = "Outros"


def pct(v, d=1):
    return f"{100 * v:.{d}f}%".replace(".", ",")


def num(v):
    return f"{v:,.0f}".replace(",", ".")


def dec(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def relative_diff(a, b):
    """Quanto a é maior que b, relativo a b. Inf se b é zero e a não."""
    if b == 0:
        return float("inf") if a > 0 else 0.0
    return (a - b) / b


def _fmt_metric(metric, v):
    return pct(v) if metric == "er" else num(v)


def _post_metric(p, metric):
    if metric == "er":
        return p["eng"] / p["imp"] if p.get("imp") and p.get("eng") is not None else None
    return p.get(metric)


# ---------------------------------------------------------------- avisos ----

def build_caveats(k, posts, months):
    """Limitações dos dados que o leitor precisa saber antes de ler as frases."""
    out = []
    if k.get("top_posts_list_truncated"):
        out.append(f"Uma lista de top posts do export chegou ao limite de {k['top_posts_list_max_rows']} linhas: "
                   "as análises por post só veem os posts de melhor desempenho. Medianas por grupo tendem a "
                   "ficar acima do real e o número de posts por mês é um mínimo, não o total.")
    if k.get("days_missing_in_coverage"):
        out.append(f"Faltam {k['days_missing_in_coverage']} dias dentro do período coberto: os exports "
                   "carregados não são contínuos.")
    if any(m["partial"] for m in months):
        out.append("Meses com dias sem dados (marcados com *) não entram nas comparações entre meses.")
    if posts:
        other = sum(1 for p in posts if p.get("topic") == OTHER_TOPIC)
        if other / len(posts) > 0.5:
            out.append(f"{other} de {len(posts)} posts não se encaixaram em nenhum tema de "
                       "seeds/topic_rules.csv. Ajuste as regras para a sua área ou use a análise com IA "
                       "(make prompt), que agrupa os posts pelos títulos.")
    out.append("Idioma estimado por palavras na URL do post; posts não reconhecidos contam como EN.")
    out.append("Métricas de post contam só o que aconteceu dentro do período de cada export.")
    w = k.get("attribution_window_days")
    if w:
        span = "do dia do post" if w == 1 else f"do dia do post e dos {w - 1} dia(s) seguinte(s)"
        out.append(f"Seguidores por post são aproximados: soma dos novos seguidores {span}, "
                   "incluindo os que viriam de qualquer forma.")
    return out


# --------------------------------------------------------------- frases -----

def concentration(k):
    if k["days_covered"] < MIN_DAYS or k.get("top10pct_days_share") is None:
        return None
    share = k["top10pct_days_share"]
    if share >= 0.5:
        shape = "concentrado em poucos dias"
    elif share <= 0.2:
        shape = "distribuído de forma estável"
    else:
        shape = "moderadamente concentrado"
    return (f"Alcance {shape}: os 10% de dias com mais impressões somaram {pct(share, 0)} do total "
            f"(se fosse uniforme, seriam 10%). Um dia típico teve {num(k['daily_impressions_median'])} impressões.")


def correlation(k):
    ce, ci = k.get("corr_followers_engagements"), k.get("corr_followers_impressions")
    if ce is None or ci is None or k["days_covered"] < MIN_DAYS:
        return None
    if max(ce, ci) < MIN_CORR:
        return (f"Novos seguidores por dia quase não acompanham impressões ({dec(ci, 2)}) nem engajamentos "
                f"({dec(ce, 2)}) do mesmo dia: o crescimento parece vir de outras fontes.")
    if ce > ci + MIN_CORR_DIFF:
        return (f"Novos seguidores acompanham mais os engajamentos (correlação {dec(ce, 2)}) do que as "
                f"impressões ({dec(ci, 2)}).")
    if ci > ce + MIN_CORR_DIFF:
        return (f"Novos seguidores acompanham mais as impressões (correlação {dec(ci, 2)}) do que os "
                f"engajamentos ({dec(ce, 2)}).")
    return (f"Novos seguidores acompanham impressões ({dec(ci, 2)}) e engajamentos ({dec(ce, 2)}) "
            f"em grau parecido.")


def baseline(k):
    if (k.get("low_activity_days") or 0) < 14 or k.get("baseline_followers_per_day") is None:
        return None
    limit = num(k["low_activity_max_impressions"])
    per_day = k["baseline_followers_per_day"]
    if per_day == 0:
        return (f"Nos {k['low_activity_days']} dias com menos impressões (até {limit} por dia) você não ganhou "
                f"seguidores: o crescimento vem dos dias com alcance.")
    return (f"Nos {k['low_activity_days']} dias com menos impressões (até {limit} por dia) você ganhou em média "
            f"{dec(per_day)} seguidor(es) por dia. Nesse ritmo, o ano todo explicaria cerca de "
            f"{pct(k['baseline_share_of_followers'] or 0, 0)} dos novos seguidores; o resto acompanha os dias com mais alcance.")


def compare_groups(posts, key, metric):
    """Compara o grupo de maior mediana com o segundo. Devolve (status, texto) ou None.

    status: 'diff' (diferença clara) ou 'same' (sem diferença clara).
    """
    groups = {}
    for p in posts:
        v = _post_metric(p, metric)
        if v is not None and p.get(key) is not None:
            groups.setdefault(p[key], []).append(v)
    if key == "topic":
        groups.pop(OTHER_TOPIC, None)
    eligible = [(g, median(vs), len(vs)) for g, vs in groups.items() if len(vs) >= MIN_POSTS_PER_GROUP]
    if len(eligible) < 2:
        return None
    eligible.sort(key=lambda t: (-t[1], -t[2], t[0]))
    (a, ma, na), (b, mb, nb) = eligible[0], eligible[1]
    fa, fb = _fmt_metric(metric, ma), _fmt_metric(metric, mb)
    if relative_diff(ma, mb) < MIN_RELATIVE_DIFF:
        return "same", f"{a} ({fa}, {na} posts) e {b} ({fb}, {nb} posts)"
    text = f"\"{a}\" teve mediana maior: {fa} ({na} posts), contra {fb} em \"{b}\" ({nb} posts)."
    if min(na, nb) < FEW_POSTS_PER_GROUP:
        text += " Com poucos posts por grupo, trate como hipótese a testar."
    return "diff", text


def group_comparisons(posts):
    out, same = [], []
    metric_names = dict(METRICS)
    for key, dim_name in DIMENSIONS:
        for metric, metric_name in METRICS:
            r = compare_groups(posts, key, metric)
            if r is None:
                continue
            status, text = r
            if status == "diff":
                out.append(f"Por {dim_name}, em {metric_names[metric]}: {text}")
            else:
                same.append(f"{dim_name} / {metric_name}: {text}")
    if same:
        out.append("Sem diferença clara (menos de "
                   f"{pct(MIN_RELATIVE_DIFF, 0)} entre as medianas) em " + "; ".join(same) + ".")
    return out


def months_without_posts(k, months):
    if k.get("top_posts_list_truncated"):
        return None  # um mês "sem posts" pode ter tido posts fora do top
    full = [m for m in months if not m["partial"]]
    with_p = [m["i"] for m in full if m["n"] > 0]
    without = [m["i"] for m in full if m["n"] == 0]
    if len(with_p) < MIN_MONTHS_PER_SIDE or len(without) < MIN_MONTHS_PER_SIDE:
        return None
    aw, awo = sum(with_p) / len(with_p), sum(without) / len(without)
    base = (f"meses sem posts ({len(without)}) tiveram em média {num(awo)} impressões e meses com posts "
            f"({len(with_p)}), {num(aw)}")
    if relative_diff(aw, awo) >= MIN_RELATIVE_DIFF:
        return f"Publicar fez diferença no mês: {base}."
    if relative_diff(awo, aw) >= MIN_RELATIVE_DIFF:
        return f"Meses sem posts tiveram mais alcance que meses com posts: {base}. Vale olhar o que aconteceu neles."
    return f"Sem diferença clara de alcance entre {base}."


def best_month(k, months):
    full = [m for m in months if not m["partial"]]
    if len(full) < 3 or max(m["f"] for m in full) == 0:
        return None
    b = max(full, key=lambda m: m["f"])
    posts = "" if k.get("top_posts_list_truncated") else f" e {b['n']} posts"
    return f"Mês com mais novos seguidores: {b['label']}, com {b['f']}{posts}."


def audience_gap(seniority):
    rows = [(v, f or 0, c or 0) for v, f, c in seniority if f is not None or c is not None]
    if len(rows) < 2:
        return None
    top_f = max(rows, key=lambda r: r[1])
    top_c = max(rows, key=lambda r: r[2])
    gap = max(rows, key=lambda r: abs(r[1] - r[2]))
    text = (f"Senioridade mais comum entre seguidores: {top_f[0]} ({pct(top_f[1], 0)}); entre quem vê o "
            f"conteúdo: {top_c[0]} ({pct(top_c[2], 0)}).")
    if abs(gap[1] - gap[2]) >= MIN_PP_GAP:
        text += (f" A maior diferença está em {gap[0]}: {pct(gap[1], 0)} dos seguidores contra "
                 f"{pct(gap[2], 0)} de quem vê o conteúdo.")
    else:
        text += " Os dois públicos têm perfil parecido (nenhuma diferença acima de 5 pontos)."
    return text


def build_highlights(k, posts, months, seniority):
    out = [concentration(k), correlation(k), baseline(k)]
    out += group_comparisons(posts)
    out += [months_without_posts(k, months), best_month(k, months), audience_gap(seniority)]
    out = [s for s in out if s]
    if not out:
        out.append(f"Ainda há poucos dados para destaques automáticos. Carregue um export com pelo menos {MIN_DAYS} dias.")
    return out
