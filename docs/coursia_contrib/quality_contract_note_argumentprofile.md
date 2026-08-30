# Contrat d'unité du score qualité — note pour `Argument_Analysis_ArgumentProfile.ipynb`

**Émetteur** : `Claude Code @ myia-ai-01:2025-Epita-Intelligence-Symbolique`
**Destinataire** : CoursIA — série `SymbolicAI/Argument_Analysis/`
**Statut** : **proposition amont**. Zéro commit de notre côté dans `D:\CoursIA`.

> **En une phrase.** Votre notebook est cohérent sous ses propres règles ; c'est *notre* fichier qui
> se contredisait. Nous le corrigeons en amont, et la migration de votre notebook préserve **tous**
> vos verdicts affichés — seule la virgule bouge.

---

## 1. Ce qui a changé chez nous

`overall` avait trois contrats d'unité qui ne s'accordaient pas. #1942 en fixe **un seul** :

> `overall` = **somme** des scores par vertu, chacun dans [0, 1], sur les vertus **évaluées**.
> Les lecteurs normalisent en divisant par `len(scores)`.

Le dénominateur varie : depuis #1923 les vertus inapplicables restent absentes, donc le plafond
dépend de l'entrée ({2, 6, 8} mesurés sur textes réels). C'est pourquoi la grandeur comparable est la
**fraction du maximum applicable**, pas une note absolue.

## 2. Ce que votre notebook enseigne — et pourquoi ce n'était pas une erreur

```python
etat.add_quality_score(a_expert, scores={"clarte": 6.0, "fondement": 2.0, "pertinence": 5.0}, overall=4.3)
```

Votre modèle est **interne­ment cohérent** : vertus sur /10, `overall` = *moyenne* des vertus
(13/3 = 4.33 ✓, 15.5/3 = 5.17 ✓, 23/3 = 7.67 ✓), seuils sur /10. C'est un choix pédagogique
défendable, et il ne pouvait pas diverger tant que la seule méthode que vous appelez —
`get_weak_arguments` — faisait une lecture **absolue**.

C'est exactement là qu'était notre incohérence : la déclaration du contrat et cette méthode vivent
dans le **même fichier**, à 580 lignes d'écart, et disaient l'inverse l'une de l'autre. Nous la
corrigeons (#1951).

## 3. Après le correctif : votre appel **lèvera**, il ne mentira pas

Nous avons délibérément écarté la normalisation silencieuse. Avec elle, votre
`get_weak_arguments(threshold=5.0)` aurait renvoyé **tous** les arguments — et le corrigé de votre
Exercice 2 serait devenu faux **sans aucun signal**. À la place :

```
ValueError: get_weak_arguments(threshold=5.0) is not a fraction: since #1942 quality
'overall' is the SUM of per-virtue [0, 1] scores and readers divide by len(scores), so
the comparison scale is [0, 1], not a note sur 10. Divide the pre-#1942 threshold by 10
(5.0 -> 0.5, the weak bar).
```

Une erreur lisible qui nomme la migration vaut mieux qu'un exercice qui donne discrètement une
mauvaise réponse à un étudiant.

## 4. La migration préserve **exactement** votre pédagogie

Vérifié numériquement — les trois verdicts, le résultat de `get_weak_arguments` et la forme de
l'Exercice 2 sont identiques :

| argument | avant (`overall` /10) | après (`sum` puis fraction) | verdict avant | verdict après |
|---|---|---|---|---|
| `a_expert` | 4.3 | somme 1.30 → **0.433** | FAIBLE | **FAIBLE** |
| `a_fauxdilemme` | 5.2 | somme 1.55 → **0.517** | MIXTE | **MIXTE** |
| `a_cout` | 7.7 | somme 2.30 → **0.767** | SOLIDE | **SOLIDE** |

`get_weak_arguments` : `['a_expert']` avant (seuil 5.0), `['a_expert']` après (seuil 0.5).
Exercice 2 : bascule à `threshold > 5.2` avant, `threshold > 0.5167` après — même exercice, sweep
`0.3 → 0.8` par pas de `0.1`.

### Cellules à modifier

**Cellule 8** — diviser les vertus par 10, et faire de `overall` leur **somme** :

```python
etat.add_quality_score(a_expert,       scores={"clarte": 0.60, "fondement": 0.20, "pertinence": 0.50}, overall=1.30)
etat.add_quality_score(a_fauxdilemme,  scores={"clarte": 0.70, "fondement": 0.25, "pertinence": 0.60}, overall=1.55)
etat.add_quality_score(a_cout,         scores={"clarte": 0.80, "fondement": 0.70, "pertinence": 0.80}, overall=2.30)
```

**Cellule 16** — `overall 4.3/10` → `fraction 0.43 du maximum applicable`.

**Cellule 18** — la comparaison doit porter sur la fraction, pas sur `overall` :

```python
qs   = p.quality_score
frac = (qs["overall"] / len(qs["scores"])) if qs else float("nan")
if   n_fall >= 1 and frac <  0.5: verdict = "FAIBLE (fallacieux+mal fonde)"
elif n_fall == 0 and frac >= 0.7: verdict = "SOLIDE"
else:                             verdict = "MIXTE"
```

**Cellule 20** — `threshold=5.0` → `threshold=0.5` ; le libellé `(overall < 5.0)` →
`(fraction < 0.5 du maximum applicable)`.

**Cellule 23** (Exercice 2) — sweep `0.3 → 0.8` pas `0.1` ; corrigé : bascule quand
`threshold > 0.517`.

### ⚠ Un défaut préexistant que la migration rend visible — Exercice 3

```python
overall_qualite * 0.4 + (1 - n_sophismes/3) * 0.3 + (1 - max_force_contre) * 0.3
```

Les deux derniers termes sont dans [0, 1] ; le premier ne l'était **déjà pas** avant (4.3 · 0.4 =
1.72 écrasait la somme). Le mélange d'unités est antérieur à notre changement, mais l'énoncé est
l'endroit naturel pour le corriger : utiliser la **fraction** (`overall / len(scores)`), pas
`overall`. Cela rend le score agrégé réellement dans [0, 1] — et l'exercice enseigne alors ce qu'il
prétend enseigner, une pondération.

## 5. Ce que nous ne faisons pas

- **Aucun push chez vous.** Ceci est une proposition ; la greffe est une PR si vous la voulez.
- **Nous ne re-taggons pas avant que le correctif soit en place.** Un tag de refresh essence poserait
  chez vous un `_shared_state.py` qui se contredit. Le tag arrive **après** #1951.
- **Nous ne touchons pas à votre choix pédagogique.** Si vous préférez garder l'échelle /10 côté
  enseignement, la migration ci-dessus n'est pas obligatoire — il suffit alors de **ne pas** re-pull
  `_shared_state.py`, et de le noter dans `NOTICE-EPITA`.

## Voir aussi

- #1942 / #1946 — le contrat unifié et les 4 lecteurs corrigés
- #1951 — `get_weak_arguments`, le 5ᵉ lecteur (ce qui vous concerne directement)
- #1949 — état réel du pin vendoré et dérive amont
