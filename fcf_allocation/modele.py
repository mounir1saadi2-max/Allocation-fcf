"""Modèle d'allocation du free cash flow (FCF).

Le FCF d'une année est réparti entre quatre usages concurrents :
investissement (IN), réduction de dette (DE), rachat d'actions (AC)
et trésorerie (RE).

La répartition se fait en deux temps :
1. les montants contraints sont réservés d'abord (plancher de rachat
   imposé par la politique actionnariale) ;
2. le reste est réparti au prorata de scores compris entre 0 et 1,
   en respectant le plafond de rachat (algorithme de remplissage).

Ainsi, contrairement à une simple normalisation des scores, les
contraintes (plancher et plafond de rachat) sont toujours respectées
et la somme des montants est exactement égale au FCF.
"""

from __future__ import annotations

from dataclasses import dataclass, field

USAGES = ("IN", "DE", "AC", "RE")
LIBELLES = {
    "IN": "Investissement",
    "DE": "Réduction de dette",
    "AC": "Rachat d'actions",
    "RE": "Trésorerie",
}


@dataclass(frozen=True)
class Parametres:
    """Hypothèses du modèle. Toutes sont modifiables et documentées dans le README."""

    # Multiplicateur du seuil de rendement selon la confiance (1 faible, 2 moyenne, 3 forte)
    prime_incertitude: dict = field(default_factory=lambda: {1: 1.7, 2: 1.3, 3: 0.9})
    # Ajustement du seuil de rendement par niveau de sécurité (+10 % par cran au-dessus de 2)
    ajust_securite: float = 0.1
    # Écart de rendement au-delà du seuil donnant un score d'investissement maximal (en multiple du coût)
    marge_investissement: float = 2.0
    # Coût de la dette à partir duquel la motivation de remboursement est maximale
    cout_dette_eleve: float = 0.08
    # Part maximale du FCF consacrée aux rachats selon la sécurité (1, 2, 3)
    plafond_rachat: dict = field(default_factory=lambda: {1: 0.6, 2: 0.5, 3: 0.4})
    # Hausse imposée des rachats pour une politique « croissante »
    hausse_politique_croissante: float = 0.05
    # Bonus de score de rachat selon la politique (0 libre, 1 constante, 2 stable, 3 croissante)
    bonus_politique: dict = field(default_factory=lambda: {0: 0.0, 1: 0.1, 2: 0.15, 3: 0.2})
    # Score minimal de trésorerie (motif de précaution incompressible)
    tresorerie_min: float = 0.05


@dataclass
class Entreprise:
    """Situation financière de l'entreprise pour une année donnée.

    Les montants sont en millions d'euros, les taux en décimal (0.05 = 5 %).
    """

    fcf: float                 # free cash flow disponible
    ebitda: float              # EBITDA, nécessaire pour suivre le levier
    dette_ebitda: float        # ratio Dette nette / EBITDA
    cout_dette: float          # taux d'intérêt de la dette
    tri: float                 # rendement attendu des projets d'investissement
    decote: float              # décote perçue de l'action (0.25 = 25 %)
    confiance: int             # confiance dans l'avenir : 1 faible, 2 moyenne, 3 forte
    securite: int              # préférence pour la sécurité : 1 faible, 2 moyenne, 3 élevée
    politique: int = 0         # rémunération actionnariale : 0 libre, 1 constante, 2 stable, 3 croissante
    rachat_precedent: float = 0.0  # rachats de l'an dernier
    levier_max: float = 3.5    # ratio Dette/EBITDA à ne pas dépasser

    def __post_init__(self) -> None:
        if self.fcf <= 0:
            raise ValueError("Le FCF doit être strictement positif.")
        if self.ebitda <= 0:
            raise ValueError("L'EBITDA doit être strictement positif.")
        if self.dette_ebitda < 0:
            raise ValueError("Le ratio Dette/EBITDA ne peut pas être négatif.")
        if self.levier_max <= 0:
            raise ValueError("Le levier maximal doit être strictement positif.")
        if not 0 <= self.cout_dette < 1:
            raise ValueError("Le coût de la dette doit être compris entre 0 et 1.")
        if not -1 < self.tri < 1:
            raise ValueError("Le TRI doit être compris entre -1 et 1.")
        if not 0 <= self.decote < 1:
            raise ValueError("La décote doit être comprise entre 0 et 1.")
        if self.confiance not in (1, 2, 3):
            raise ValueError("La confiance doit valoir 1, 2 ou 3.")
        if self.securite not in (1, 2, 3):
            raise ValueError("La sécurité doit valoir 1, 2 ou 3.")
        if self.politique not in (0, 1, 2, 3):
            raise ValueError("La politique doit valoir 0, 1, 2 ou 3.")
        if self.rachat_precedent < 0:
            raise ValueError("Les rachats précédents ne peuvent pas être négatifs.")

    @property
    def dette(self) -> float:
        return self.dette_ebitda * self.ebitda


def _borne(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- Scores (entre 0 et 1) -------------------------------------------------

def seuil_rendement(e: Entreprise, p: Parametres = Parametres()) -> float:
    """Rendement minimal exigé : coût de la dette majoré par l'incertitude et la sécurité."""
    return p.prime_incertitude[e.confiance] * e.cout_dette * (1 + p.ajust_securite * (e.securite - 2))


def score_investissement(e: Entreprise, p: Parametres = Parametres()) -> float:
    seuil = seuil_rendement(e, p)
    if e.tri < seuil:
        return 0.0
    marge = p.marge_investissement * e.cout_dette * (1 + p.ajust_securite * (e.securite - 2))
    if marge == 0:
        return 1.0
    return _borne((e.tri - seuil) / marge)


def score_dette(e: Entreprise, p: Parametres = Parametres()) -> float:
    """Plus le levier est proche du plafond, la dette chère et l'avenir incertain, plus on rembourse."""
    if e.dette <= 0:
        return 0.0
    if e.dette_ebitda >= e.levier_max:
        return 1.0
    levier = e.dette_ebitda / e.levier_max
    poids_levier = 0.4 + 0.1 * e.securite
    cout = min(1.0, e.cout_dette / p.cout_dette_eleve)
    incertitude = (3 - e.confiance) / 2
    return _borne(poids_levier * levier + 0.3 * cout + 0.2 * incertitude)


def score_rachat(e: Entreprise, p: Parametres = Parametres()) -> float:
    """Racheter est d'autant plus intéressant que l'action est décotée et l'avenir jugé favorable."""
    return _borne(e.decote * e.confiance / 3 + p.bonus_politique[e.politique])


def score_tresorerie(e: Entreprise, p: Parametres = Parametres()) -> float:
    """Motif de précaution : incertitude, préférence pour la sécurité et levier élevé."""
    incertitude = (3 - e.confiance) / 2
    securite = (e.securite - 1) / 2
    levier = min(1.0, e.dette_ebitda / e.levier_max)
    return max(p.tresorerie_min, _borne(0.4 * incertitude + 0.3 * securite + 0.3 * levier))


def scores(e: Entreprise, p: Parametres = Parametres()) -> dict:
    return {
        "IN": score_investissement(e, p),
        "DE": score_dette(e, p),
        "AC": score_rachat(e, p),
        "RE": score_tresorerie(e, p),
    }


# --- Allocation sous contraintes -------------------------------------------

def plafond_rachat(e: Entreprise, p: Parametres = Parametres()) -> float:
    return p.plafond_rachat[e.securite] * e.fcf


def plancher_rachat(e: Entreprise, p: Parametres = Parametres()) -> float:
    """Montant minimal de rachat imposé par la politique, dans la limite du plafond."""
    if e.politique == 2:
        voulu = e.rachat_precedent
    elif e.politique == 3:
        voulu = e.rachat_precedent * (1 + p.hausse_politique_croissante)
    else:
        voulu = 0.0
    return min(voulu, plafond_rachat(e, p))


def allouer(e: Entreprise, p: Parametres = Parametres()) -> dict:
    """Répartit le FCF. Renvoie un dict {usage: montant en M€} dont la somme vaut le FCF."""
    s = scores(e, p)
    montants = {u: 0.0 for u in USAGES}

    # 1. Réserver les montants contraints
    montants["AC"] = plancher_rachat(e, p)
    reste = e.fcf - montants["AC"]

    # La dette ne peut pas être remboursée au-delà de son encours
    plafonds = {"IN": float("inf"), "DE": e.dette, "AC": plafond_rachat(e, p), "RE": float("inf")}

    # 2. Répartir le reste au prorata des scores, en respectant les plafonds
    actifs = {u for u in USAGES if s[u] > 0 and montants[u] < plafonds[u]}
    while reste > 1e-9 and actifs:
        total = sum(s[u] for u in actifs)
        sature = set()
        distribue = 0.0
        for u in actifs:
            part = reste * s[u] / total
            place = plafonds[u] - montants[u]
            ajout = min(part, place)
            montants[u] += ajout
            distribue += ajout
            if ajout >= place - 1e-9:
                sature.add(u)
        reste -= distribue
        if not sature:
            break
        actifs -= sature

    # Ce qui ne peut être placé nulle part reste en trésorerie
    montants["RE"] += max(0.0, reste)
    return montants


def parts(montants: dict) -> dict:
    total = sum(montants.values())
    return {u: montants[u] / total for u in montants}
