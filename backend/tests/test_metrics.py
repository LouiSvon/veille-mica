import pytest

from app.evaluation.metrics import mrr, premier_rang, recall_at_k, wilson


def test_wilson_valeurs_connues():
    bas, haut = wilson(7, 10)
    assert bas == pytest.approx(0.397, abs=0.002) and haut == pytest.approx(0.892, abs=0.002)
    bas, haut = wilson(0, 10)
    assert bas == 0.0 and haut == pytest.approx(0.278, abs=0.002)
    bas, haut = wilson(10, 10)
    assert haut == 1.0 and bas == pytest.approx(0.722, abs=0.002)


def test_wilson_aucune_donnee_ne_promet_rien():
    assert wilson(0, 0) == (0.0, 1.0)


def test_wilson_l_intervalle_se_resserre_avec_n():
    petit = wilson(5, 10)
    grand = wilson(50, 100)
    assert (grand[1] - grand[0]) < (petit[1] - petit[0])


def test_recall_et_mrr():
    rangs = [1, 3, None, 6]
    assert recall_at_k(rangs, 5) == (2, 4)
    assert recall_at_k(rangs, 1) == (1, 4)
    assert mrr(rangs) == pytest.approx((1 + 1 / 3 + 0 + 1 / 6) / 4)
    assert mrr([]) == 0.0


def test_premier_rang():
    assert premier_rang(["a", "b", "c"], {"c", "b"}) == 2
    assert premier_rang(["a", "b"], {"z"}) is None
    assert premier_rang([], {"a"}) is None
