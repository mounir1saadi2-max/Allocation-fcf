"""Interface en ligne de commande.

    python -m fcf_allocation.cli            # saisie interactive
    python -m fcf_allocation.cli --exemple  # cas d'exemple
"""

from __future__ import annotations

import argparse

from .modele import LIBELLES, USAGES, Entreprise, allouer, parts
from .projection import projeter


def demander(question: str, type_=float, choix=None, defaut=None):
    while True:
        brut = input(question + (f" [{defaut}]" if defaut is not None else "") + " : ").strip()
        if not brut and defaut is not None:
            return defaut
        try:
            valeur = type_(brut.replace(",", "."))
        except ValueError:
            print("  Valeur invalide, merci de réessayer.")
            continue
        if choix is not None and valeur not in choix:
            print(f"  Choisissez parmi {sorted(choix)}.")
            continue
        return valeur


def saisir() -> Entreprise:
    print("Aide à la décision : allocation du free cash flow (montants en M€, taux en décimal)\n")
    politique = demander("Politique actionnariale (0 libre, 1 constante, 2 stable, 3 croissante)", int, {0, 1, 2, 3})
    return Entreprise(
        fcf=demander("Free cash flow disponible"),
        ebitda=demander("EBITDA"),
        dette_ebitda=demander("Ratio Dette nette / EBITDA"),
        levier_max=demander("Ratio Dette/EBITDA à ne pas dépasser", defaut=3.5),
        cout_dette=demander("Coût de la dette (ex : 0.05)"),
        tri=demander("Rendement attendu des investissements (ex : 0.10)"),
        decote=demander("Décote perçue de l'action (ex : 0.25)"),
        confiance=demander("Confiance dans l'avenir (1 faible, 2 moyenne, 3 forte)", int, {1, 2, 3}),
        securite=demander("Préférence pour la sécurité (1 faible, 2 moyenne, 3 élevée)", int, {1, 2, 3}),
        politique=politique,
        rachat_precedent=demander("Rachats d'actions de l'an dernier", defaut=0.0) if politique in (2, 3) else 0.0,
    )


def exemple() -> Entreprise:
    return Entreprise(fcf=100, ebitda=200, dette_ebitda=2.8, cout_dette=0.05, tri=0.12,
                      decote=0.20, confiance=2, securite=2, politique=3, rachat_precedent=20)


def afficher_allocation(e: Entreprise) -> None:
    m = allouer(e)
    p = parts(m)
    print("\nRépartition du FCF")
    for u in USAGES:
        print(f"  {LIBELLES[u]:<20} {p[u]:>6.1%}   {m[u]:>8.1f} M€")


def afficher_projection(e: Entreprise, annees: int, croissance: float) -> None:
    print(f"\nProjection sur {annees} ans (croissance organique {croissance:.1%})")
    print(f"  {'Année':<6}{'FCF':>8}{'Dette/EBITDA':>14}{'IN':>8}{'DE':>8}{'AC':>8}{'RE':>8}")
    for r in projeter(e, annees, croissance):
        print(f"  {r['annee']:<6}{r['fcf']:>8.1f}{r['dette_ebitda']:>14.2f}"
              f"{r['IN']:>8.1f}{r['DE']:>8.1f}{r['AC']:>8.1f}{r['RE']:>8.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Allocation du free cash flow")
    parser.add_argument("--exemple", action="store_true", help="lancer le cas d'exemple")
    parser.add_argument("--annees", type=int, default=0, help="nombre d'années de projection")
    parser.add_argument("--croissance", type=float, default=0.03, help="croissance organique annuelle")
    args = parser.parse_args()

    e = exemple() if args.exemple else saisir()
    afficher_allocation(e)
    annees = args.annees if args.exemple else demander("\nAnnées de projection (0 pour aucune)", int, defaut=0)
    if annees:
        croissance = args.croissance if args.exemple else demander("Croissance organique annuelle", defaut=0.03)
        afficher_projection(e, annees, croissance)


if __name__ == "__main__":
    main()
