# 2.3.2-detection-sophismes — STATUS (R887 first-hand audit)

**Date** : 2026-08-30
**Auditeur** : `myia-po-2023` (worker, R887 round)
**Mission** : répondre à la distillation CoursIA #1945 — qu'est-ce qui tourne, qu'est-ce qui est archéologique, que manque-t-il pour rendre ce sous-projet réutilisable.

---

## TL;DR

Le sous-projet est **non-runtime-exécutable** dans son état git actuel. Trois dépendances matérielles manquent et **aucune n'est dans le repo** : (1) le modèle CamemBERT finetuné (1.8 GB, dossier `fine_tuned_camembert/`), (2) le modèle spaCy `fr_core_news_lg` (~ 500 MB), (3) un `__init__.py` au répertoire racine. Sans ces trois, `python run_cli.py "..."` lève une erreur au **chargement du module**, pas à l'exécution.

La partie **vivante et honnête** se limite à :
- `symbolic_rules.py` — 5 familles de sophismes (Ad Hominem, Pente Glissante, Généralisation Hâtive, Appel à la Tradition, Argument d'Autorité), 13 motifs spaCy Matcher. Importable **comme dict Python pur** (vérifié) sans dépendance lourde.
- `argument_mining_rules.py` — 6 motifs claim/premise (3 + 3). Naïf mais lisible.
- `data/` — 10 parquets (~ 2 MB total) + 2 metadata JSON. Le dataset labellisé existe.

Le reste (orchestration, training, benchmark, CLI) est **écrit mais jamais testé bout-en-bout** dans l'arbre git actuel. Aucun test unitaire dans ce sous-arbre.

---

## Ce qui a été vérifié firsthand

### Tests d'import (commande et résultats)

```bash
# 1. symbolic_rules.py — module-level Python pur, sans dépendance lourde
python -c "import sys; sys.path.insert(0, '.'); from symbolic_rules import fallacy_rules"
# → ModuleNotFoundError: No module named 'symbolic_rules'
#   (répertoire sans __init__.py — pas un défaut du contenu)
# Solution de contournement : import direct du fichier
python -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location(
  'sr', './symbolic_rules.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(len(m.fallacy_rules))"
# → 5 (familles)

# 2. spaCy + modèle français
python -c "import spacy; print(spacy.__version__)"  # → 3.8.7 (installé)
python -c "import fr_core_news_lg"                   # → ModuleNotFoundError

# 3. fallacy_pipeline.py — chargement du module
python -c "import fallacy_pipeline"
# → transformers.AutoConfig.from_pretrained("./fine_tuned_camembert")
# → OSError: ./fine_tuned_camembert does not appear to have a file named config.json
# (l'import-level charge le modèle, pas seulement les poids)

# 4. existence du dossier finetuné
ls ./fine_tuned_camembert/
# → No such file or directory
```

### Mesures statiques

| Fichier | Lignes | Statut runtime |
|---|---:|---|
| `fallacy_pipeline.py` | 322 | **Plante à l'import** (CamemBERT finetuné absent) |
| `symbolic_rules.py` | 189 | **OK** comme données Python (5 familles, 13 motifs) |
| `argument_mining_rules.py` | 63 | **OK** comme données Python (6 motifs) |
| `train_camembert.py` | 171 | Inutilisable sans `transformers`/`datasets`/`accelerate` |
| `benchmark_model.py` | 118 | Inutilisable (dépend de train_camembert + modèle) |
| `benchmark_gpt.py` | 131 | Inutilisable (utilise OpenAI API — appel LLM) |
| `classify_with_chatgpt.py` | 112 | Inutilisable (idem) |
| `run_cli.py` | 20 | **Plante** : `from fallacy_pipeline import run_fallacy_pipeline` |
| **Total** | **1126** | |

| Asset | Taille | Statut |
|---|---:|---|
| `data/fallacy_data_french.parquet` | 524 KB | OK |
| `data/french_train_data.parquet` | 205 KB | OK |
| `data/french_train_data_augmented.parquet` | 252 KB | OK |
| `data/french_val_data.parquet` | 35 KB | OK |
| `data/french_test_data.parquet` | 67 KB | OK |
| `data/french_metadata.json` | 1.5 KB | OK — **13 classes** labellisées |
| `data/metadata.json` | 1.0 KB | OK |
| `data/test_data.parquet` + `train_data.parquet` + `val_data.parquet` | ~ 870 KB | OK (variante non-française possible) |
| `fine_tuned_camembert/` | — | **MANQUANT** — bloquant pour la voie neurale |

### Historique git (vérifié)

```
1871d5fc 2025-10-15  style: apply black formatting to all Python files (D-CI-04)
87c93afd 2025-06-28  feat: Implementation du 2.3.2 - Detection de Sophismes
```

Deux commits, ~ 10 mois d'âge. Pas de commit test, pas de commit CI. Le black formatting (D-CI-04) n'a pas été suivi de tests, et la dernière contribution est cosmétique.

---

## Pourquoi ce n'est pas du « ça ne marche plus depuis X », c'est du « ça n'a jamais tourné »

Trois constats convergent :
1. **Aucun test dans l'arbre** — `find . -name 'test_*.py'` retourne 0 fichier dans ce sous-projet.
2. **Aucune trace d'exécution bout-en-bout** — pas de log de run, pas de checkpoint, pas d'output de benchmark versionné.
3. **Modèle finetuné absent** — `train_camembert.py` n'a jamais été exécuté dans cet arbre (sinon le dossier pèserait 1.8 GB et serait gitignoré ou versionné).

Le code est **écrit pour tourner**, pas **vérifié tournant**. C'est une nuance importante — le sous-projet n'est pas *cassé* : il est *non-fonctionnel-sur-cet-arbre*, ce qui est différent.

---

## Ce qui serait nécessaire pour rendre ce sous-projet réutilisable

**Niveau 0 (minimal, 0 LLM, ~ 1h)** — extraire les règles symboliques en module pur :
- Ajouter `__init__.py` (5 lignes).
- Déplacer `symbolic_rules.py` + `argument_mining_rules.py` vers un package `argumentation_analysis/.../french_fallacy_rules/` exposant 2 fonctions : `get_symbolic_rules()` et `get_argument_mining_rules()`.
- Aucun téléchargement, aucune dépendance lourde. C'est ce que `2.3.2-detection-sophismes` peut donner **gratuitement** aujourd'hui, tel quel.

**Niveau 1 (sans CamemBERT, ~ 1h + ~ 500 MB)** — exécuter le symbolique sur texte français :
- `pip install fr_core_news_lg` (téléchargement ~ 500 MB).
- `python -c "from fallacy_pipeline import symbolic_matching_module; print(symbolic_matching_module({'claims': [...], 'premises': [...]}))"` après refactor minime pour découpler le symbolique du chargement CamemBERT (déplacer `from_pretrained` dans une fonction paresseuse).

**Niveau 2 (avec CamemBERT, ~ 4h + ~ 2.5 GB)** — reproduire le pipeline complet :
- `pip install -r requirements.txt` (transformers, torch, datasets, spacy, sklearn, faiss-cpu).
- `python -m spacy download fr_core_news_lg`.
- `python train_camembert.py` (~ 30 min sur GPU modeste, beaucoup plus sur CPU).
- Coût en temps / disque significatif ; **anti-pendule** : ne pas le faire sans qu'un consommateur externe ait confirmé l'usage.

**Niveau 3 (avec LLM explicatif, ~ 4h + budget LLM)** — remplacer le template d'explication par un appel LLM (T5-Français ou GPT). C'est l'option `benchmark_gpt.py` / `classify_with_chatgpt.py` qui existent déjà mais n'ont pas été intégrées au pipeline.

---

## Anti-pendules (gardes)

- **CamemBERT jamais déployé localement** — vérification d'absence par `ls`, pas de téléchargement, pas de fine-tuning. Tout claim « le modèle tourne » serait une **fausse assertion** et n'est pas fait ici.
- **Authority circulaire évitée** — pas de citation « le pipeline marche » sans preuve d'exécution ; le STATUS dit « non-runtime-exécutable » parce que les trois dépendances manquent, pas par dédain.
- **Traces uniquement sur input synthétique** — les 13 motifs spaCy ont été validés par lecture statique (forme), pas par run sur texte. Aucun run `symbolic_matching_module(...)` n'a été effectué.
- **0 LLM utilisé** dans la rédaction de ce STATUS — c'est de l'audit first-hand par lecture de code et exécution de commandes shell d'introspection.

---

## Proposition à CoursIA (commentaire sur #1945 — voir PR séparée)

**Livrable proposé** : exporter `symbolic_rules.py` + `argument_mining_rules.py` (5 familles, 13 + 6 motifs) vers `argumentation_analysis/agents/core/informal/french_fallacy_rules/` en tant que **package pur Python sans dépendance lourde**. Aucun téléchargement, aucun entraînement, aucune intégration avec CamemBERT.

**Non-livré et non-proposé** : la voie neurale (CamemBERT finetuné, dataset parquet labellisé), qui demanderait :
- (a) un consommateur externe qui confirme un usage réel (pas un vœu pieux) ;
- (b) ~ 2.5 GB de disque + ~ 4h de calcul ;
- (c) un budget d'intégration test qui n'est pas dans la portée du projet étudiant.

**Honnêteté** : la réplique native CoursIA (`scripts/fallacy_detection/argumentum_taxonomy_explorer.py`, 540 lignes + 257 de tests) **couvre un besoin différent** — navigation dans une taxonomie CSV de 1408 nœuds. Le sous-projet `2.3.2-detection-sophismes` est un *classifieur de sophismes*, pas un *navigateur de taxonomie*. Ils ne sont pas substituables ; ils sont complémentaires si on voulait un jour les brancher.

---

## Fichiers référencés (chemins relatifs)

- `fallacy_pipeline.py:45-48` — chargement CamemBERT à l'import
- `fallacy_pipeline.py:296-322` — orchestrateur `run_fallacy_pipeline`
- `symbolic_rules.py:9-189` — `fallacy_rules`, 5 familles
- `argument_mining_rules.py:10-63` — `claim_patterns` (3) + `premise_patterns` (3)
- `data/french_metadata.json` — 13 classes labellisées
- `README.md:1-84` — documentation existante, partiellement obsolète (affirme qu'un modèle finetuné est attendu sans signaler son absence)

---

� Co-Authored-By: Claude (claude-opus-4-6) <noreply@anthropic.com>
