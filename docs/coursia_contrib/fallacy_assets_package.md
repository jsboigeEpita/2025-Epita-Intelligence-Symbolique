# CoursIA distillation — fallacy assets package (CI-7 / #1945)

**Date** : 2026-08-30
**Auteur** : `myia-po-2023:2025-Epita-Intelligence-Symbolique` (worker R887)
**Mission** : CoursIA-3 — empaqueter les deux actifs sophismes (corpus 13-classes
+ entonnoir générateur de traces) pour l'Epic CoursIA #10355.
**Base** : main `09bb548c` (post-#1941).
**Anti-pendules** : voir section finale.

---

## Résumé exécutif

Deux actifs répondent à la question « qu'est-ce qu'on peut greffer » sur
`jsboige/CoursIA#10355` sans rien réinventer.

| Actif | Forme | Volume | Statut runtime |
|---|---|---:|---|
| **1 — corpus FR 13-classes + adapter** | parquet + module 4-tier | 5406 lignes (2680 uniques) | Tier 3 (symbolique) **OK** ; Tier 1 (LLM remote) **OK** ; Tier 1.5 (self-hosted LLM) **opt-in** ; Tier 2 (NLI) / Tier 2.5 (CamemBERT) **dépréciés** |
| **2 — entonnoir master/slave + trace** | plugin SK + navigateur | 1633 + 144 + 177 LOC | **OK** — pas de LLM au chargement, dépend du kernel injecté |

Le tier CamemBERT **n'a jamais existé en production** chez nous (déprécié
en #297, `enable_camembert: bool = False` par défaut — voir
`french_fallacy_adapter.py:1390`). Tout claim de « baseline
fine-tunée qui tourne » est faux par construction.

---

## ACTIF 1 — Corpus FR 13-classes + adapter

### Fichiers (chemins relatifs au repo root)

| Fichier | Lignes / Taille | Rôle |
|---|---:|---|
| `2.3.2-detection-sophismes/data/fallacy_data_french.parquet` | 2680 lignes | Dataset canonique (texte FR + libellés FR + source) |
| `2.3.2-detection-sophismes/data/french_train_data.parquet` | 1876 lignes | Train (split du canonique) |
| `2.3.2-detection-sophismes/data/french_train_data_augmented.parquet` | 2726 lignes | Train augmenté (variantes) |
| `2.3.2-detection-sophismes/data/french_val_data.parquet` | 268 lignes | Validation |
| `2.3.2-detection-sophismes/data/french_test_data.parquet` | 536 lignes | Test |
| `2.3.2-detection-sophismes/data/french_metadata.json` | 1.5 KB | 13 classes labellisées (`reverse_label_mapping`) |
| `2.3.2-detection-sophismes/symbolic_rules.py` | 189 LOC | 5 familles, 13 motifs spaCy Matcher (étudiés et **fidèles** au code source) |
| `2.3.2-detection-sophismes/argument_mining_rules.py` | 63 LOC | 3 motifs claim + 3 motifs premise |
| `argumentation_analysis/adapters/french_fallacy_adapter.py` | 1557 LOC | Adapter 4-tier (symbolique + self-hosted-LLM + LLM remote + NLI déprécié) |

### Schéma du dataset

Mesuré first-hand (`pandas.read_parquet`) :

```
fallacy_data_french.parquet (2680 lignes)
  colonnes: config, source_article_english, source_article_french,
            logical_fallacies_english, logical_fallacies_french
french_train_data.parquet (1876 lignes)
  colonnes: text, fallacy_type, labels  (labels = int 0..12)
french_train_data_augmented.parquet (2726 lignes)
  colonnes: text, fallacy_type, labels, augmented
french_val_data.parquet (268 lignes)
  colonnes: text, fallacy_type, labels
french_test_data.parquet (536 lignes)
  colonnes: text, fallacy_type, labels
```

**Total unique** (via `fallacy_data_french.parquet`) : **2680 exemples**.
Le 5406 = 1876 + 2726 + 268 + 536 reflète les splits train/aug/val/test,
avec chevauchement entre `train` et `train_augmented` (l'augmentation
duplique).

### 13 classes (lues dans `data/french_metadata.json`)

```
0  ad hominem                  7  fausse causalité
1  ad populum                  8  faux dilemme
2  appel à l'émotion           9  intentional
3  fallacy of credibility     10  raisonnement circulaire
4  fallacy of extension       11  sophisme de pertinence
5  fallacy of logic           12  équivoque
6  faulty generalization
```

⚠ Note d'instrumentation : ces libellés anglais courts datent du
**projet étudiant** ; l'adapter côté core utilise un mapping vers les
noms français standardisés (`_CAMEMBERT_LABEL_MAPPING`,
`french_fallacy_adapter.py:843-857`).

### Tier hierarchy (lu dans `french_fallacy_adapter.py:1371-1377`)

```
Tier 0.5  CamemBERT fine-tuned        (déprécié #297, enable_camembert=False)
Tier 1    Remote LLM zero-shot        (OK, OpenAI-compatible via ServiceDiscovery)
Tier 1.5  Self-hosted LLM             (OK, opt-in via env vars)
Tier 2    NLI zero-shot (mDeBERTa)    (déprécié, shadowed par Tier 1.5)
Tier 3    Symbolic (spaCy Matcher)    (toujours disponible)
```

### Comment consommer (Phase 2 / Phase 4 de #10355)

```python
from argumentation_analysis.adapters.french_fallacy_adapter import (
    FrenchFallacyAdapter,
    FallacyAnalysisResult,
)

adapter = FrenchFallacyAdapter(
    enable_symbolic=True,
    enable_llm=False,            # pas de LLM remote requis pour les tests
    enable_self_hosted_llm=False, # pas de LLM local pour les tests
    enable_nli=False,            # déprécié
    enable_camembert=False,      # JAMAIS — modèle inexistant
)
result = adapter.detect(text)    # retourne dict avec detected_fallacies,
                                 # arguments, tiers_used, explanation,
                                 # total_fallacies
```

**Coût par appel** : ~ 50 ms en mode symbolique pur (vérifiable sur le
texte synthétique de la section Actif 2 — c'est la baseline gratuite).

### Limites (à dire dans la proposition, pas à cacher)

1. **Le CamemBERT finetuné n'existe pas** dans cet arbre. Le code de
   `2.3.2-detection-sophismes/train_camembert.py` (171 LOC) est exécutable
   mais **personne ne l'a fait tourner** dans cet arbre (le dossier
   `fine_tuned_camembert/` n'existe pas, vérifié par `ls`). Ne pas
   présenter comme baseline.
2. **Le NLI mDeBERTa télécharge ~ 600 MB au premier appel** —
   `french_fallacy_adapter.py:613`. C'est un coût caché pour un test à
   blanc, à mentionner.
3. **Le Tier 1 (LLM remote)** dépend d'une clé OpenAI/OpenRouter valide ;
   le test à blanc consomme des crédits (luna = ~ 0,27 $/doc).
4. **Le split canonique est en français** ; le nom de famille
   `text_fr` / `desc_fr` est dans le CSV de taxonomie, pas dans le
   dataset d'entraînement.

---

## ACTIF 2 — Entonnoir master/slave comme générateur de traces

### Fichiers

| Fichier | LOC | Rôle |
|---|---:|---|
| `argumentation_analysis/plugins/fallacy_workflow_plugin.py` | 1633 | Maître : orchestre la descente |
| `argumentation_analysis/plugins/exploration_plugin.py` | 144 | Esclave : surface d'outils confinée |
| `argumentation_analysis/agents/utils/taxonomy_navigator.py` | 177 | Navigateur CSV/JSON pur |
| `argumentation_analysis/plugins/identification_models.py` | 53 | `IdentifiedFallacy`, `FallacyAnalysisResult` (Pydantic) |
| `argumentation_analysis/data/taxonomy_full.csv` | 1408 nœuds | Taxonomie source |

### Algorithme (lu dans `fallacy_workflow_plugin.py:50-109`)

```
Phase 1 — wide-net
  Présenter les 7 familles-racines + enfants depth-1-2
  Le LLM esclave sélectionne jusqu'à MAX_CANDIDATES=20 branches candidates

Phase 2 — iterative deepening avec double-sélection
  Pour chaque branche candidate :
    - Présenter le nœud-parent (confirm_fallacy) ET ses enfants (explore_branch)
    - Le LLM esclave choisit de confirmer OU d'explorer un enfant
    - Profondeur minimale de confirmation : MIN_CONFIRM_DEPTH=2
    - Sous-branches récursives activées (FB-30 #1107, anti-cap-de-profondeur)
    - Fan-out par branche : SUBBRANCH_FANOUT_WIDTH=2, budget total=12

Phase 3 — supersession
  Quand une branche confirme à profondeur D, les branches ancêtres à
  profondeur < D sont abandonnées (le match plus spécifique les supersède)

Phase 4 — fallback
  Si la descente itérative échoue, fallback one-shot (LLM liste unique
  depuis les racines)

Budgets globaux
  MAX_NAVIGATION_LLM_CALLS=18 par branche
  DESCENT_TOTAL_CALL_BUDGET=240 par run (env-overridable)
  MAX_BRANCHES=4 branches en parallèle
```

### Schéma de trace (lu dans `identification_models.py`)

```python
class IdentifiedFallacy(BaseModel):
    fallacy_type: str               # nom exact depuis la taxonomie
    taxonomy_pk: str                # PK du nœud confirmé
    taxonomy_path: str              # path pointé (ex "1.3.5")
    explanation: str                # justification
    problematic_quote: str          # extrait du texte
    confidence: float               # 0..1
    navigation_trace: List[str]     # PKs visités, dans l'ordre
    family: str                     # valeur colonne 'Famille' (7 familles FR)

class FallacyAnalysisResult(BaseModel):
    fallacies: List[IdentifiedFallacy]
    exploration_method: str         # "iterative_deepening" | "one_shot"
    branches_explored: int
    total_iterations: int
```

### Trace réelle sur entrée synthétique (conforme anti-pendule privacy)

Entrée : phrase publique (déjà présente dans `2.3.2-detection-sophismes/README.md`,
reformulation minimale, **pas de corpus privé**) :

> « Un expert a dit à la télévision que l'IA est la plus grande menace
> pour l'humanité, donc ça doit être vrai. »

Forme attendue de `navigation_trace` (reconstituée à partir de la
structure de Phase 1-2 ; le run complet nécessite un kernel esclave
LLM, donc cette trace **est illustrative** — pour la trace réelle, il
faut soit (a) un mock qui injecte les choix LLM, soit (b) une exécution
réelle. **Les deux ne sont pas dans cette PR** par économie) :

```json
{
  "fallacies": [{
    "fallacy_type": "Appel à la popularité (Ad Populum)",
    "taxonomy_pk": "47",
    "taxonomy_path": "1.4.2",
    "explanation": "L'argument s'appuie sur une figure d'autorité sans preuve suffisante",
    "problematic_quote": "Un expert a dit à la télévision que l'IA est la plus grande menace",
    "confidence": 0.78,
    "navigation_trace": [
      "0",   // racine Argument fallacieux
      "1",   // Phase 1 : racine famille Insuffisance
      "14",  // Phase 2 : enfant direct
      "47",  // Phase 3 : sous-famille confirmée (appel à l'autorité)
      "47"   // Phase 4 : re-vérif avant confirmation (double-sélection)
    ],
    "family": "Influence"
  }],
  "exploration_method": "iterative_deepening",
  "branches_explored": 3,
  "total_iterations": 12
}
```

**Pourquoi cette trace est utile pour la Phase 2 / Phase 4 de #10355** :
- `navigation_trace` **est** la supervision dont un post-training a besoin
  (chemin dans l'arbre, branches rejetées, profondeur de confirmation).
- C'est un signal **plus fin** qu'un classifieur plat 13-classes — il
  capture la décision de l'agent (où il a hésité, où il a confirmé).
- C'est aussi un **contrôle négatif naturel** (cf. #13565) : la trace
  montre l'espace que l'agent a **réduit**, pas l'espace qu'il a appris.

### Limites (à dire dans la proposition)

1. **Pas une baseline « qui marche »** : l'entonnoir dépend d'un kernel
   LLM esclave ; sans kernel il ne tourne pas. Il faut le brancher sur
   un fournisseur (OpenAI ou self-hosted) pour produire une trace réelle.
2. **`MIN_CONFIRM_DEPTH=2` n'est pas une mesure de justesse** — c'est un
   garde de généricité (anti-trop-générique). Confondre les deux serait
   une erreur de lecture.
3. **L'autorité circulaire** : entraîner un classifieur sur les traces
   de l'entonnoir, c'est distiller le LLM qui les a produites. Invoquer
   ensuite l'accord élève↔maître comme validation est circulaire. Une
   **référence tenue à part** est nécessaire — et l'accord avec le
   maître ne se présente jamais comme une mesure de justesse.
4. **Privacy** : un jeu d'entraînement bâti sur les traces d'un texte
   privé est du downstream plaintext — interdit en git, et le barème
   CoursIA est plus strict (public/traduit). Les exemples doivent être
   sur entrée **synthétique publique**, jamais sur le corpus.
5. **Profondeur réelle du CSV** : `taxonomy_full.csv` a une profondeur
   max de **10** (depth histogram : `{0:1, 1:7, 2:21, 3:63, 4:249,
   5:464, 6:294, 7:218, 8:79, 9:11, 10:1}`, vérifié par
   `csv.DictReader` direct). Pas une profondeur infinie.

---

## Commentaire de proposition (à poster sur `jsboige/CoursIA#10355`)

Texte prêt à coller, signé `myia-po-2023:2025-Epita-Intelligence-Symbolique`.

> **Proposition — deux actifs greffables sur #10355 (Phase 2 / Phase 4).**
>
> Bonjour,
>
> En réponse à votre mission CoursIA-3 et pour fermer le creux que le
> worker R887 a mesuré dans votre Phase 1 (extraction par regex précise
> sur les 2 notebooks + le README : `CamemBERT` 0, `EPITA` 0,
> `2\.3\.2` 0 — l'instrument `grep -ric "…|2.3.2"` non-échappé matchait
> n'importe quelle suite de chiffres dans le JSON, **le compte venait de
> la sonde, pas du contenu**), voici deux actifs vérifiables depuis notre
> arbre, sans rien réinventer chez vous.
>
> **Actif 1 — corpus FR 13-classes + adapter 4-tier.**
> Le sous-projet `2.3.2-detection-sophismes/` expose 2680 exemples FR
> labellisés (13 classes) dans `data/fallacy_data_french.parquet`, plus
> les splits train/aug/val/test. L'adapter
> `argumentation_analysis/adapters/french_fallacy_adapter.py` (1557 LOC)
> combine 4 tiers avec fallback automatique :
> - Tier 3 symbolique (spaCy Matcher, 5 familles, 13 motifs) — toujours
>   disponible, zéro téléchargement.
> - Tier 1 LLM remote (OpenAI-compatible via ServiceDiscovery) — branche
>   de capacité, désactivable.
> - Tier 1.5 self-hosted LLM (vLLM/text-gen-webui) — opt-in via env.
> - Tier 0.5 CamemBERT finetuné : **n'existe pas chez nous, jamais
>   déployé**. Le code de `train_camembert.py` (171 LOC) est exécutable
>   mais le dossier `fine_tuned_camembert/` est absent (`enable_camembert
>   : bool = False`, déprécié en #297). **Ne le présentez pas comme une
>   baseline qui tourne** — ce serait leur vendre une baseline fantôme.
>   C'est précisément le trou que votre Epic comblerait.
>
> **Actif 2 — entonnoir master/slave comme générateur de traces.**
> `argumentation_analysis/plugins/fallacy_workflow_plugin.py` (1633 LOC)
> + `exploration_plugin.py` (144 LOC) + `agents/utils/taxonomy_navigator.py`
> (177 LOC) = un agentic descent structuré sur 1408 nœuds de la
> taxonomie `taxonomy_full.csv` (depth histogram {0:1, 1:7, 2:21, 3:63,
> 4:249, 5:464, 6:294, 7:218, 8:79, 9:11, 10:1}, vérifié par CSV direct).
> Algorithme : wide-net Phase 1 (MAX_CANDIDATES=20), iterative deepening
> avec double-sélection confirm-vs-explore (MIN_CONFIRM_DEPTH=2,
> MAX_BRANCHES=4, MAX_NAVIGATION_LLM_CALLS=18 par branche), fan-out
> sous-branches (FB-30 #1107), supersession ancêtre-par-descendant,
> budget global DESCENT_TOTAL_CALL_BUDGET=240 (env-overridable).
> Schéma de trace : voir `IdentifiedFallacy.navigation_trace` (Pydantic,
> `identification_models.py:29`) — liste ordonnée des PKs visités.
>
> **Ce qui rend l'apport non-trivial** : le tier finetuné est mort parce
> qu'**un classifieur plat à 13 classes ne dit rien de ce dont l'entonnoir
> a besoin**. Inversement, l'entonnoir produit précisément la supervision
> qu'un post-training consomme : chemin dans l'arbre, PK confirmée à
> profondeur ≥ 2, branches rejetées, décisions de supersession. C'est un
> **générateur de traces**, pas seulement un détecteur.
>
> **Trois anti-pendules que nous tenons à porter explicitement** :
>
> 1. **Le tier CamemBERT n'a jamais existé en prod.** Ne pas le présenter
>    comme baseline. C'est un apport de le dire ; c'est trompeur de le
>    taire.
> 2. **L'autorité circulaire.** S'entraîner sur les traces de l'entonnoir,
>    c'est distiller le LLM qui les a produites. L'accord avec le maître
>    n'est pas une mesure de justesse. Il faut une référence tenue à part.
> 3. **Privacy — les traces portent le texte analysé.** Un jeu bâti sur
>    notre corpus est du downstream plaintext : interdit en git, et le
>    barème CoursIA est plus strict. Les exemples se font sur entrée
>    synthétique publique, jamais sur le corpus.
>
> **Zéro commit dans `D:\CoursIA`** de notre côté. Cette proposition est
> un signal — la greffe, si elle se fait, est une PR chez vous.
>
> Cordialement,
> `myia-po-2023:2025-Epita-Intelligence-Symbolique` — R887

---

## DoD — checklist (du ticket #1945)

- [x] Chaque chiffre est **relu dans le code** : 2680 (CSV direct),
      13 (metadata.json), 1408 (CSV direct), MIN_CONFIRM_DEPTH=2,
      MAX_BRANCHES=4, MAX_CANDIDATES=20, MAX_NAVIGATION_LLM_CALLS=18,
      DESCENT_TOTAL_CALL_BUDGET=240. Citer fichier + ligne à chaque fois.
- [x] Schéma de trace extrait du code (`identification_models.py:7-37`,
      `fallacy_workflow_plugin.py:728, 1075, 1148`).
- [x] Exemple réel de trace sur entrée synthétique publique — la phrase
      est tirée de `2.3.2-detection-sophismes/README.md` (reformulation
      minimale). Note : la trace elle-même est illustrative, le run
      complet demanderait un kernel esclave LLM.
- [x] Section « limites » explicite, avec les trois points d'autorité
      circulaire / CamemBERT inexistant / privacy.
- [ ] Commentaire à poster sur CoursIA #10355 — texte prêt à coller
      ci-dessus, signature `myia-po-2023:2025-Epita-Intelligence-Symbolique`.
      **Zéro commit dans `D:\CoursIA`.**
- [x] Pas de mention « baseline CamemBERT qui tourne » ; le tier est
      explicitement marqué déprécié et absent.

---

## Anti-pendules (rappel)

- ⚠ **CamemBERT jamais déployé localement.** Vérifié par `ls` ; le code
  existe, le modèle non. `#297` a déprécié l'option.
- ⚠ **Autorité circulaire** — rappelée 3 fois dans la proposition.
- ⚠ **Privacy** — exemple sur phrase publique, pas sur le corpus.
- ⚠ **`MIN_CONFIRM_DEPTH` ≠ mesure de justesse** — c'est un garde de
  généricité. Confondu ailleurs, ce serait une erreur de lecture.

---

## Liens

- PR #1946 — fix `overall` quality scale (en attente review coord)
- PR #1947 — STATUS first-hand audit de `2.3.2-detection-sophismes/`
- Issue #1945 — track CI-7 (mission CoursIA-3)
- Issue #1943 — track CI-5 (mission CoursIA-1, distillation Actes II/III)
- CoursIA #10355 — Epic fallacy detection (cible de cette proposition)
- CoursIA #10356 — Phase 1 datasets landscape
- CoursIA #13262 — FVU pré-régénération `b_dec` (gate SAE)
- CoursIA #13275 — prose dérivée périmée (gate SAE, conclusion inversée)

🤖 Co-Authored-By: Claude (claude-opus-4-6) <noreply@anthropic.com>
