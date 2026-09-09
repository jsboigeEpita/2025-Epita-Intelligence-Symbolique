# Validation indépendante — strate 6, notebook de recollement

**Signature :** `Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique`
**Objet :** réexécution indépendante de `Argument_Analysis_Recollement_Strate6.ipynb`
(commit `1bc80e5d`, `#13041`), validation de l'affirmation « le glue OOF bat le
spécialiste sur la zone disputée ».

## Méthode

- **Pin examiné :** `1bc80e5d6` — commit qui ne touche **que** `...Argument_Analysis_Recollement_Strate6.ipynb` (1961 insertions, confirmé par `git show --stat`). Aucun autre fichier modifié par le commit.
- **Exécution :** dans un **git worktree temporaire détaché** (`git worktree add --detach <temp> 1bc80e5d`), dans le sous-dossier `MyIA.AI.Notebooks/SymbolicAI/Argument_Analysis/`. Le working tree de `D:\dev\CoursIA` (HEAD flottant `32cf333a6`, arbre sale) n'a **pas** été touché — aucun checkout in-place, aucun commit CoursIA.
- **Environnement :** `python 3.10` (env `projet-is-roo-new`) + `rdflib 7.6.0` (importé depuis les site-packages de base, **sans installation** — rdflib est pur Python). Libs : `pandas`, `numpy`, `sklearn 1.7.2`, `networkx`. Aucun LLM, aucune API, aucune JVM, aucun `pip install`.
- **Runner :** cellules de code exécutées **dans l'ordre**, dans un namespace partagé, stdout capturé par cellule (pas de dépendance à `nbconvert`/`jupyter` — absents de l'env).
- **Trace de réexécution :** le stdout par cellule de cette exécution est committé à côté du présent document (`s6_recollement_exec_log.txt`) — la cellule 32 du log est la table de verdict citée en §2.
- **Mutations :** deux variantes du notebook (voir §4), exécutées dans le même worktree.

**Portée du snapshot.** Cette validation certifie le **snapshot `#13070`** (pin `1bc80e5d`) et lui seul.
Le même notebook a ensuite été modifié par `#13606` puis par `#14355` (`116db0b0`) : **l'état courant
du dépôt CoursIA post-`#14355` n'est pas certifié ici** — ni ses chiffres, ni l'exécution de ses
cellules. Toute extension de la validation à cet état courant exigerait une ré-exécution au
nouveau pin.

## 1. Exécution

**18/18 cellules de code** s'exécutent sans erreur (les 22 cellules markdown sont descriptives). Tous les
intermédiaires s'évaluent : lecture RDF (rdflib, `1 388` revendications), lecture LEX, lecture STRUCT,
lecture GRAPH, matrice de compatibilité, compétence par famille, règles de fusion, verdict, sensibilité.

Données présentes au pin : `data/argumentum_fallacies_taxonomy.csv` (1408 × 102) et
`ontologies/argumentum_fallacies.owl` ; le graphe N-Triples (`..._converted.nt`) est produit par la
cellule de conversion mécanique. Reproduit `argumentum_fallacies_converted.nt` du chemin attendu.

## 2. Verdict mesuré (firsthand) — la revendication centrale

Rappel du contexte : quatre « lectures » (RDF, LEX, STRUCT, GRAPH) revendiquent chacune une
couverture et produisent une prédiction ; le « glue » est une **fusion apprise par validation
croisée** (OOF) ; le « spécialiste » est la lecture la plus forte au sens du train
(**GRAPH**, accuracy train 0.996). La **zone disputée** = entrées à ≥3 revendications en
désaccord (1 076 / 1 407 ; test = 334).

| règle | test global | test disputé |
|---|---|---|
| R1 majorité brute | 52.2 % | 45.2 % |
| R2 précision globale | 56.3 % | 50.3 % |
| **GLU apprise (OOF)** | **61.0 %** | **56.6 %** |
| **SPEC GRAPH seul** | **55.8 %** | **49.7 %** |
| ORACLE (borne sup) | 76.4 % | 75.7 % |
| lecture RDF seule | 33.3 % | 21.6 % |
| lecture LEX seule | 53.0 % | 46.1 % |
| lecture STRUCT seule | 39.0 % | 28.4 % |
| lecture GRAPH seule | 55.8 % | 49.7 % |

**Verdict : l'affirmation est confirmée.** Sur la zone disputée, le glue OOF (56.6 %) **bat** le
meilleur spécialiste (GRAPH, 49.7 %) d'**+6,9 points** ; il le bat aussi sur le test global
(61.0 % vs 55.8 %, +5,2 points). Le glue dépasse les deux règles de fusion naïves (majorité brute,
précision globale) et se situe sous la borne oracle (75.7 %) — un gain réel mais non saturé.
NB : SPECIAL GRAPH seul et lecture GRAPH seule sont identiques (le spécialiste EST la lecture GRAPH).

## 3. Compatibilité entre lectures (contexte du recollement)

Taux de contradiction sur le chevauchement des revendications :

|  | RDF | LEX | STRUCT | GRAPH |
|---|---|---|---|---|
| RDF | 0.0 % | 61.6 % | 50.6 % | 61.0 % |
| LEX | 61.6 % | 0.0 % | 56.9 % | 11.3 % |
| STRUCT | 50.6 % | 56.9 % | 0.0 % | 56.7 % |
| GRAPH | 61.0 % | 11.3 % | 56.7 % | 0.0 % |

Incompatibilité moyenne (hors diagonale) : **49.7 %**. LEX et GRAPH sont très proches (11.3 % de
contradiction), les autres paires ~50-60 % — c'est la « zone disputée » que le glue doit arbitrer.

## 4. Discipline de fuite — contrôle de mutation

**Mécanique vérifiée (cellule d'assertion)** : `BANNED_CSV` exclut **31 colonnes** porteuses de la
position/réponse (`PK`, `path`, `decimal_path*`, `depth*`, `Famille*`, `Sous-Famille`, `Soussousfamille`,
`Family*`, `Subfamily*`, `Subsubfamily*`…) par regex, et l'assertion verrouille qu'aucune ne fuit
dans les blocs LEX/STRUCT. `struct_frame()` (lecture STRUCT) **n'inclut explicitement aucune** de ces
colonnes `Famille`/`decimal_path`/`depth`. Côté OWL, le backbone (`skos:broader`, `skos:narrower`,
`rdfs:subClassOf`) est banni de la lecture RDF.

**Mutations tentées** (pour vérifier qu'un retrait de discipline ferait fuiter la réponse) :
1. *Injection dans `FEATURE_COLS["STRUCT"]`* — n'a **pas** atteint le modèle : `struct_frame()` construit
   ses colonnes explicitement, indépendamment de `FEATURE_COLS` ; verdict **byte-identique**.
2. *Injection directe de `decimal_path` + `Famille` dans `struct_frame()`* — échec
   `ValueError: could not convert string to float` : le pipeline routé vers `StandardScaler`
   (colonne numérique) rejette la chaîne du chemin. L'injection d'un encodeur de position exigerait
   aussi de recâbler le `ColumnTransformer` (rattacher un `OneHotEncoder`), ce qui dépasse une
   simple mutation.

**Interprétation honnête** : je n'ai **pas** obtenu de contrôle de fuite positif (aucune inflation
d'accuracy lors des mutations). Ce que cela établit : (a) la discipline est **mécaniquement** en place
(regex + assertion + exclusion explicite dans `struct_frame`), et (b) elle est structurellement
robuste — une colonne de position ne peut pas « glisser » dans le pipeline numérique sans être
explicitement recâblée. **Ce n'est pas** une démonstration de fuite ni de non-fuite définitive ;
c'est le constat que la garde tient et que la construction du contrôle positif est non triviale.

## 5. Limites

- Re-mesure **déterministe** (aucun LLM, aucune API) : la revendication est reproductible au pin, mais
  les chiffres dépendent de la graine `SEED` du notebook et de la version de `sklearn` (1.7.2) —
  une version différente peut donner des marges légèrement décalées.
- La comparaison porte sur **un pilote** (notebook strate-6, une partition train/test), pas sur une
  campagne de référence multi-runs. Ceci ne certifie pas la valeur générale du recollement sur d'autres
  corpus.
- Le notebook contient **3 exercises à compléter** (`#2161`) — non remplis ici, hors périmètre
  de validation.
- La notion de « zone disputée » (≥3 revendications, désaccord) est celle du notebook ; je n'ai pas
  re-mesuré une définition alternative.

## 6. Provenance

- Examinateur : `myia-po-2025` (worker), dans le cadre du dispatch coord `/worker-round`.
- Commit examiné : `1bc80e5d6` (pin), arbre de travail temporaire ; `D:\dev\CoursIA` non modifié.
- Aucun run LLM, aucune API, aucun `pip install`, aucun changement système.
- Référence immuable conservée telle quelle (aucune réécriture/re-render).
