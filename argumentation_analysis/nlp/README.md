# `nlp/` — utilitaires d'embeddings

## Rôle et frontière

Un seul module : `embedding_utils.py` — génération et persistance d'embeddings par chunks. L'`__init__.py` du package est **entièrement commenté** : aucun export effectif.

N'est **pas** la couche NLP d'analyse (tokenisation/sophismes vivent dans [`adapters/`](../adapters/README.md) et `agents/informal/`) : ici seulement les embeddings.

## Composants publics

- `get_embeddings_for_chunks(...)` (`embedding_utils.py:44`) — embeddings par chunk de texte ;
- `save_embeddings_data(embeddings_data, output_path)` (`embedding_utils.py:168`) — persistance vers un fichier (retour booléen).

L'`__init__.py` documente `embedding_utils` (:14) mais son export est commenté (:18 `# from .embedding_utils import generate_embeddings`, :21 `# "generate_embeddings",`) — **le nom exporté n'existe pas** dans le module (les fonctions réelles sont celles ci-dessus) : le commentaire est un fossile d'une API renommée.

## Points d'entrée valides

Un seul importeur : [`pipelines/embedding_pipeline.py:70`](../pipelines/embedding_pipeline.py) — qui importe `get_embeddings_for_chunks` directement depuis `embedding_utils` (contournant l'`__init__` vide). **Mais** `embedding_pipeline.py` lui-même n'a **aucun importeur production** (grep plein dépôt) — la chaîne s'arrête un maillon plus haut. `utils/dev_tools/project_structure_utils.py:24` ne fait que nommer le package dans un mapping descriptif.

## Amont / aval

- Amont : service d'embeddings (OpenAI), chunks de textes.
- Aval : `pipelines/embedding_pipeline.py` (orphelin à son tour) ; fichiers d'embeddings si `save_embeddings_data` est appelé.

## Statut d'intégration

**résiduel (à un maillon)** — l'unique importeur production est lui-même sans consommateur ; couverture réelle uniquement par les tests.

## Artefacts et lecteurs

`save_embeddings_data` écrit un fichier d'embeddings à l'`output_path` fourni — aucun appelant production, donc aucun artefact produit en pratique.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/nlp/ tests/unit/argumentation_analysis/pipelines/test_embedding_pipeline.py -v
```

(suite dédiée `tests/unit/argumentation_analysis/nlp/test_embedding_utils.py` + tests du pipeline consommateur).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `nlp/`. Frères : [`pipelines/`](../pipelines/README.md) (le consommateur orphelin), [`adapters/`](../adapters/README.md) (NLP de détection).

## Limites connues

- `__init__.py` : export commenté référençant un symbole inexistant (`generate_embeddings`) — fossile d'API renommée, trompeur à la lecture ;
- chaîne morte à un maillon : `nlp` ← `embedding_pipeline` ← personne ;
- aucun export effectif : tout import doit cibler `argumentation_analysis.nlp.embedding_utils` explicitement.
