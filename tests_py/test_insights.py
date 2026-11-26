"""Testes das frases automáticas com contas simuladas.

Garante que nenhuma frase afirma algo que os dados não sustentam, para contas
de qualquer tamanho e ritmo. Rode com: make test
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import insights as ins  # noqa: E402


def kpis(**over):
    base = dict(
        days_covered=365, days_missing_in_coverage=0, daily_impressions_median=500,
        top10pct_days_share=0.35, corr_followers_engagements=0.4, corr_followers_impressions=0.4,
        low_activity_days=90, low_activity_max_impressions=200, baseline_followers_per_day=2.0,
        baseline_share_of_followers=0.5, top_posts_list_truncated=False, top_posts_list_max_rows=30,
        attribution_window_days=3,
    )
    base.update(over)
    return base


def posts(groups, key="lang", topic="Outros", fmt="texto/link"):
    """groups: {valor: [(impressões, engajamentos), ...]}"""
    out = []
    for value, items in groups.items():
        for imp, eng in items:
            p = dict(d="2026-01-01", imp=imp, eng=eng, topic=topic, lang="EN", fmt=fmt, title="x", fol=0)
            p[key] = value
            out.append(p)
    return out


def months(spec):
    """spec: lista de (posts, impressões); todos completos."""
    return [dict(label=f"m{i}", n=n, i=imp, e=0, f=10 + i, partial=False) for i, (n, imp) in enumerate(spec)]


class Concentration(unittest.TestCase):
    def test_stable_reach_is_not_called_concentrated(self):
        s = ins.concentration(kpis(top10pct_days_share=0.15))
        self.assertIn("estável", s)
        self.assertNotIn("concentrado", s)

    def test_spiky_reach(self):
        self.assertIn("concentrado em poucos dias", ins.concentration(kpis(top10pct_days_share=0.7)))

    def test_short_history_has_no_sentence(self):
        self.assertIsNone(ins.concentration(kpis(days_covered=10)))


class Correlation(unittest.TestCase):
    def test_three_outcomes_and_weak(self):
        self.assertIn("mais os engajamentos", ins.correlation(kpis(corr_followers_engagements=0.6, corr_followers_impressions=0.3)))
        self.assertIn("mais as impressões", ins.correlation(kpis(corr_followers_engagements=0.3, corr_followers_impressions=0.6)))
        self.assertIn("grau parecido", ins.correlation(kpis(corr_followers_engagements=0.5, corr_followers_impressions=0.45)))
        self.assertIn("quase não acompanham", ins.correlation(kpis(corr_followers_engagements=0.1, corr_followers_impressions=0.05)))


class Baseline(unittest.TestCase):
    def test_threshold_comes_from_the_account(self):
        self.assertIn("até 2.000 por dia", ins.baseline(kpis(low_activity_max_impressions=2000)))

    def test_no_followers_on_quiet_days(self):
        s = ins.baseline(kpis(baseline_followers_per_day=0, baseline_share_of_followers=0))
        self.assertIn("não ganhou seguidores", s)

    def test_too_few_quiet_days(self):
        self.assertIsNone(ins.baseline(kpis(low_activity_days=5)))


class GroupComparisons(unittest.TestCase):
    def test_similar_groups_say_no_clear_difference(self):
        p = posts({"PT": [(100, 2)] * 6, "EN": [(110, 2)] * 6})
        out = ins.group_comparisons(p)
        self.assertTrue(any(s.startswith("Sem diferença clara") for s in out))
        self.assertFalse(any("teve mediana maior" in s for s in out))

    def test_winner_follows_the_data_in_both_directions(self):
        a = ins.compare_groups(posts({"A": [(1000, 10)] * 6, "B": [(100, 1)] * 6}), "lang", "imp")
        b = ins.compare_groups(posts({"A": [(100, 1)] * 6, "B": [(1000, 10)] * 6}), "lang", "imp")
        self.assertTrue(a[1].startswith('"A"'))
        self.assertTrue(b[1].startswith('"B"'))

    def test_small_groups_are_left_out(self):
        p = posts({"PT": [(1000, 50)] * 4, "EN": [(10, 0)] * 4})
        self.assertEqual(ins.group_comparisons(p), [])

    def test_few_posts_is_flagged_as_hypothesis(self):
        r = ins.compare_groups(posts({"A": [(1000, 10)] * 6, "B": [(100, 1)] * 6}), "lang", "imp")
        self.assertIn("hipótese", r[1])
        r = ins.compare_groups(posts({"A": [(1000, 10)] * 20, "B": [(100, 1)] * 20}), "lang", "imp")
        self.assertNotIn("hipótese", r[1])

    def test_unmatched_topic_is_not_a_group(self):
        p = posts({"Outros": [(1000, 10)] * 20, "Vendas": [(100, 1)] * 20}, key="topic")
        self.assertIsNone(ins.compare_groups(p, "topic", "imp"))


class Months(unittest.TestCase):
    def test_truncated_lists_suppress_post_counts(self):
        k = kpis(top_posts_list_truncated=True, top_posts_list_max_rows=50)
        m = months([(0, 100), (0, 100), (5, 1000), (5, 1000)])
        self.assertIsNone(ins.months_without_posts(k, m))
        self.assertNotIn("posts", ins.best_month(k, m))

    def test_months_without_posts_can_win(self):
        s = ins.months_without_posts(kpis(), months([(0, 1000), (0, 1000), (5, 100), (5, 100)]))
        self.assertIn("mais alcance que meses com posts", s)

    def test_posting_helps(self):
        s = ins.months_without_posts(kpis(), months([(0, 100), (0, 100), (5, 1000), (5, 1000)]))
        self.assertIn("fez diferença", s)

    def test_no_clear_difference(self):
        s = ins.months_without_posts(kpis(), months([(0, 100), (0, 100), (5, 110), (5, 110)]))
        self.assertTrue(s.startswith("Sem diferença clara"))


class Audience(unittest.TestCase):
    def test_generic_labels_and_similar_profiles(self):
        s = ins.audience_gap([["Gerente", 0.40, 0.42], ["Diretor", 0.30, 0.31]])
        self.assertIn("Gerente", s)
        self.assertIn("perfil parecido", s)

    def test_gap_is_reported(self):
        self.assertIn("maior diferença está em Junior", ins.audience_gap([["Junior", 0.10, 0.40], ["Senior", 0.5, 0.3]]))


class Caveats(unittest.TestCase):
    def test_truncation_and_gaps_are_reported(self):
        c = " ".join(ins.build_caveats(kpis(top_posts_list_truncated=True, top_posts_list_max_rows=50,
                                            days_missing_in_coverage=12), [], months([(1, 1)])))
        self.assertIn("limite de 50", c)
        self.assertIn("Faltam 12 dias", c)

    def test_unmatched_topics_are_reported(self):
        c = " ".join(ins.build_caveats(kpis(), posts({"EN": [(1, 0)] * 10}), []))
        self.assertIn("10 de 10 posts não se encaixaram", c)


class SyntheticAccounts(unittest.TestCase):
    """Contas inteiras: nenhuma frase pode trazer conclusão pronta."""

    ACCOUNTS = {
        "pequena": (kpis(daily_impressions_median=8, low_activity_max_impressions=2, baseline_followers_per_day=0.1),
                    posts({"PT": [(30, 1)] * 3})),
        "grande e estável": (kpis(daily_impressions_median=50000, top10pct_days_share=0.14,
                                  low_activity_max_impressions=30000),
                             posts({"EN": [(50000, 900)] * 30, "ES": [(52000, 950)] * 30})),
        "posta todo dia": (kpis(top_posts_list_truncated=True, top_posts_list_max_rows=50, attribution_window_days=1),
                           posts({"EN": [(3000, 60)] * 50})),
        "histórico curto": (kpis(days_covered=7, low_activity_days=2), []),
    }

    def test_every_account_gets_sound_sentences(self):
        for name, (k, p) in self.ACCOUNTS.items():
            with self.subTest(conta=name):
                m = months([(1, 10)] * 4) if k["days_covered"] >= 120 else []
                out = ins.build_highlights(k, p, m, [])
                caveats = ins.build_caveats(k, p, [])
                self.assertTrue(out)
                for s in out:
                    self.assertNotIn(" mas ", s, "frase supõe um contraste")
                    self.assertNotIn("None", s)
                    self.assertNotIn("nan", s)
                if k["top10pct_days_share"] < 0.5:
                    self.assertFalse(any("concentrado em poucos dias" in s for s in out))
                if k["top_posts_list_truncated"]:
                    self.assertTrue(any("limite de 50" in c for c in caveats))
                if k["days_covered"] < ins.MIN_DAYS:
                    self.assertTrue(out[0].startswith("Ainda há poucos dados"))


if __name__ == "__main__":
    unittest.main()
