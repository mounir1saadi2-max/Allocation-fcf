import pytest

from fcf_allocation import Entreprise, Parametres, allouer, projeter, scores
from fcf_allocation.modele import plafond_rachat, plancher_rachat


def entreprise(**kw):
    base = dict(fcf=100, ebitda=200, dette_ebitda=2.0, cout_dette=0.04, tri=0.20,
                decote=0.10, confiance=3, securite=2, politique=0, rachat_precedent=0)
    base.update(kw)
    return Entreprise(**base)


def test_somme_egale_fcf():
    for conf in (1, 2, 3):
        for sec in (1, 2, 3):
            e = entreprise(confiance=conf, securite=sec, politique=3, rachat_precedent=30)
            assert sum(allouer(e).values()) == pytest.approx(e.fcf)


def test_plancher_politique_croissante_respecte():
    # Bug de la version initiale : 21 M€ au lieu de 42 M€
    e = entreprise(politique=3, rachat_precedent=40)
    assert allouer(e)["AC"] >= 42 - 1e-9


def test_plafond_rachat_respecte():
    # Bug de la version initiale : 46 % au lieu de 40 % maximum
    e = entreprise(cout_dette=0.01, dette_ebitda=0.5, decote=0.9, tri=0.0, securite=3, politique=3)
    assert allouer(e)["AC"] <= plafond_rachat(e) + 1e-9


def test_plancher_limite_par_plafond():
    e = entreprise(politique=2, rachat_precedent=500, securite=3)
    assert plancher_rachat(e) == pytest.approx(40)
    assert allouer(e)["AC"] == pytest.approx(40)


def test_pas_de_remboursement_au_dela_de_la_dette():
    e = entreprise(dette_ebitda=0.05, cout_dette=0.07)  # dette de 10 M€
    assert allouer(e)["DE"] <= 10 + 1e-9


def test_score_tresorerie_sensible_au_levier():
    s = [scores(entreprise(dette_ebitda=g, confiance=2))["RE"] for g in (0.5, 1, 2, 3)]
    assert s == sorted(s) and len(set(s)) == 4


def test_dette_chere_pousse_au_remboursement():
    bas = scores(entreprise(cout_dette=0.02))["DE"]
    haut = scores(entreprise(cout_dette=0.07))["DE"]
    assert haut > bas


def test_levier_au_plafond_force_le_remboursement():
    assert scores(entreprise(dette_ebitda=3.6))["DE"] == 1.0


def test_investissement_nul_sous_le_seuil():
    assert scores(entreprise(tri=0.01))["IN"] == 0.0


@pytest.mark.parametrize("champ,valeur", [("fcf", 0), ("confiance", 4), ("securite", 0),
                                           ("politique", 5), ("decote", 1.2), ("ebitda", -1)])
def test_saisies_invalides(champ, valeur):
    with pytest.raises(ValueError):
        entreprise(**{champ: valeur})


def test_projection_dynamique():
    e = entreprise(cout_dette=0.06, dette_ebitda=3.0, confiance=2)
    r = projeter(e, 5, croissance=0.0)
    # Le remboursement fait baisser le levier
    assert r[-1]["dette_ebitda"] < r[0]["dette_ebitda"]
    # Investissement et intérêts économisés augmentent le FCF
    assert r[1]["fcf"] > r[0]["fcf"]


def test_parametres_modifiables():
    p = Parametres(plafond_rachat={1: 0.2, 2: 0.2, 3: 0.2})
    e = entreprise(decote=0.9, tri=0.0)
    assert allouer(e, p)["AC"] <= 20 + 1e-9
