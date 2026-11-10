# Allocation du free cash flow : un outil d'aide à la décision

Que doit faire une entreprise de son free cash flow (FCF) ? Investir, se désendetter, racheter ses actions ou garder de la trésorerie ? Ce projet traduit cet arbitrage classique de finance d'entreprise en règles explicites, puis simule leurs conséquences sur plusieurs années.

L'outil ne prétend pas calculer une allocation « optimale » au sens mathématique : c'est un **modèle de scoring sous contraintes**, dont toutes les hypothèses sont visibles et modifiables. L'objectif est de rendre un raisonnement financier transparent et discutable, pas de le remplacer.

## Exemple

```bash
python -m fcf_allocation.cli --exemple --annees 5
```

```
Répartition du FCF
  Investissement        19.4%       19.4 M€
  Réduction de dette    27.1%       27.1 M€
  Rachat d'actions      32.8%       32.8 M€
  Trésorerie            20.8%       20.8 M€

Projection sur 5 ans (croissance organique 3.0%)
  Année      FCF  Dette/EBITDA      IN      DE      AC      RE
  1        100.0          2.80    19.4    27.1    32.8    20.8
  2        106.7          2.59    18.2    24.2    45.4    18.9
  3        113.3          2.40    17.3    21.9    56.6    17.4
  4        119.8          2.23    18.7    22.8    59.9    18.4
  5        126.8          2.06    20.3    23.7    63.4    19.4
```

Sans l'option `--exemple`, le programme pose les questions une à une et vérifie chaque saisie.

## Logique économique

Chaque usage du cash reçoit un score entre 0 et 1, qui traduit son attrait compte tenu de la situation de l'entreprise.

| Usage | Augmente quand… | Diminue quand… |
|---|---|---|
| **Investissement** | le rendement des projets (TRI) dépasse nettement le seuil exigé | l'avenir est incertain ou la préférence pour la sécurité forte (le seuil monte) |
| **Réduction de dette** | le levier approche du plafond, la dette est chère, l'avenir est incertain | la dette est faible ou peu coûteuse |
| **Rachat d'actions** | l'action est décotée et l'avenir jugé favorable ; la politique de distribution est engageante | l'action est correctement valorisée |
| **Trésorerie** | l'incertitude, la préférence pour la sécurité et le levier sont élevés (motif de précaution) | la situation est sereine |

Le **seuil de rendement** des investissements vaut `coût de la dette × prime d'incertitude × ajustement de sécurité`. Le coût de la dette sert ici de proxy du coût du capital : dans une version plus complète, on utiliserait le coût moyen pondéré du capital (CMPC).

## Allocation sous contraintes

La répartition se fait en deux temps, pour que les contraintes soient **toujours** respectées :

1. **Montants contraints d'abord.** Une politique « stable » impose de racheter au moins autant que l'an dernier, une politique « croissante » au moins 5 % de plus. Ce plancher est réservé avant toute répartition, dans la limite du plafond.
2. **Répartition du reste au prorata des scores**, par un algorithme de remplissage : si un usage atteint son plafond (part maximale de rachats selon la sécurité, encours de dette pour le remboursement), l'excédent est redistribué entre les autres usages.

La somme des montants est exactement égale au FCF.

## Projection dynamique

Sur plusieurs années, les décisions ont des conséquences :

- rembourser de la dette réduit l'encours, donc le levier, et les intérêts payés, ce qui augmente le FCF suivant ;
- investir augmente le FCF futur du rendement des projets ;
- les rachats d'une année deviennent la référence de la suivante.

Ce dernier point produit un **effet cliquet** visible dans l'exemple : avec une politique de rachat « croissante », le plancher augmente chaque année et les rachats montent jusqu'au plafond. C'est cohérent avec ce qu'on observe empiriquement (les entreprises réduisent difficilement une distribution annoncée), et cela montre le coût d'opportunité d'un engagement de distribution trop rigide.

## Hypothèses et paramètres

Toutes les valeurs numériques du modèle sont regroupées dans la classe `Parametres` (`fcf_allocation/modele.py`) : primes d'incertitude, plafonds de rachat par niveau de sécurité, hausse imposée par une politique croissante, etc. Elles reflètent des ordres de grandeur raisonnables mais **ne sont pas calibrées sur des données**. On peut les modifier sans toucher au code :

```python
from fcf_allocation import Entreprise, Parametres, allouer

e = Entreprise(fcf=100, ebitda=200, dette_ebitda=2.8, cout_dette=0.05, tri=0.12,
               decote=0.20, confiance=2, securite=2, politique=3, rachat_precedent=20)
prudent = Parametres(plafond_rachat={1: 0.3, 2: 0.25, 3: 0.2})
print(allouer(e, prudent))
```

## Limites et pistes d'amélioration

- Les poids des scores sont fixés à la main ; une calibration sur des données d'entreprises cotées (allocation observée du FCF) permettrait de les estimer.
- Le passage d'un scoring à une véritable optimisation (maximisation d'une fonction objectif sous contraintes, par exemple avec `scipy.optimize`) rendrait l'allocation optimale au sens strict.
- La fiscalité, les dividendes et le coût des fonds propres ne sont pas modélisés.

## Structure

```
fcf_allocation/
  modele.py       scores, contraintes et allocation
  projection.py   simulation pluriannuelle
  cli.py          interface en ligne de commande
tests/
  test_modele.py  tests (contraintes, cohérence économique, saisies invalides)
```

## Installation et tests

Python 3.9 ou plus, aucune dépendance pour l'outil lui-même.

```bash
pip install -r requirements-dev.txt
python -m pytest
```
