"""Projection pluriannuelle où les décisions de chaque année ont des conséquences.

- Rembourser de la dette réduit l'encours, donc le levier, et les intérêts payés.
- Investir augmente le FCF futur du rendement des projets (TRI).
- Les rachats de l'année deviennent la référence de l'année suivante.
"""

from __future__ import annotations

from dataclasses import replace

from .modele import Entreprise, Parametres, allouer


def projeter(e: Entreprise, annees: int, croissance: float = 0.0,
             p: Parametres = Parametres()) -> list[dict]:
    """Simule `annees` années. `croissance` est la croissance organique annuelle
    du FCF et de l'EBITDA (0.03 = 3 %). Renvoie une ligne par année."""
    if annees < 1:
        raise ValueError("Le nombre d'années doit être au moins 1.")
    resultats = []
    tresorerie = 0.0
    for annee in range(1, annees + 1):
        m = allouer(e, p)
        tresorerie += m["RE"]
        resultats.append({"annee": annee, "fcf": e.fcf, "dette_ebitda": e.dette_ebitda,
                          "tresorerie_cumulee": tresorerie, **m})

        dette = max(0.0, e.dette - m["DE"])
        ebitda = e.ebitda * (1 + croissance)
        fcf = (e.fcf * (1 + croissance)
               + e.tri * m["IN"]              # rendement des investissements
               + e.cout_dette * m["DE"])      # intérêts économisés
        e = replace(e, fcf=fcf, ebitda=ebitda, dette_ebitda=dette / ebitda,
                    rachat_precedent=m["AC"])
    return resultats
