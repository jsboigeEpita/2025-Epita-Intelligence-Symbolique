# `nlp/` — utilitaires d'embeddings

## Rôle et frontière

Un seul module : `embedding_utils.py` — génération et persistance d'embeddings par chunks. L'`__init__.py` du package est **entièrement commenté** : aucun export effectif.

N'est **pas** la couche NLP d'analyse (tokenisation/sophismes vivent dans [`adapters/`](../adapters/README.md) et `agents/informal/`) : ici seulement les embeddings.

## Composants publics

- `get_embeddings_for_chunks(...)` (`embedding_utils.py:44`) — embeddings par chunk de texte ;
- `save_embeddings_data(embeddings_data, output_path)` (`embedding_utils.py:168`) — persistance vers un fichier (retour booléen).

L'`__init__.py` documente `embedding_utils` (:14) mais son export est commenté (:18 `# from .embedding_utils import generate_embeddings`, :21 `# "generate_embeddings",`) — **le nom exporté n'existe pas** dans le module (les fonctions réelles sont celles ci-dessus) : le commentaire est un fossile d'une API renommée.

## Points d'entrée valides

**Zéro importeur production** depuis le retrait du maillon orphelin `pipelines/embedding_pipeline.py` (#2116, décision A1) — ce pipeline était l'unique importeur et n'avait lui-même aucun consommateur. Le package est conservé comme **seul détenteur local de la capacité embeddings** (l'alternative externe est le service HTTP Kernel Memory, `services/semantic_index_service.py`), capacité **épinglée par test direct** (voir Tests représentatifs). `utils/dev_tools/project_structure_utils.py:24` ne fait que nommer le package dans un mapping descriptif.

## Amont / aval

- Amont : service d'embeddings (OpenAI ou Sentence Transformers local), chunks de textes.
- Aval : personne en production ; fichiers d'embeddings si `save_embeddings_data` est appelé.

## Statut d'intégration

**dormant gardé** — aucun importeur production, mais la capacité est mesurée par une garde à embeddings réels (dimensions + pluralité sur entrée synthétique) : le module ne peut pas redevenir un candidat retrait silencieux sans faire rouge.

## Artefacts et lecteurs

`save_embeddings_data` écrit un fichier d'embeddings à l'`output_path` fourni — aucun appelant production, donc aucun artefact produit en pratique.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/nlp/ -v
```

(suite dédiée `tests/unit/argumentation_analysis/nlp/test_embedding_utils.py` + **garde de capacité** `test_embedding_capacity_guard_2116.py` : embeddings réels via Sentence Transformers `all-MiniLM-L6-v2`, 384 dimensions, pluralité assertée — aucun mock).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `nlp/`. Frères : [`pipelines/`](../pipelines/README.md) (l'ancien maillon orphelin a été retiré, #2116 A1), [`adapters/`](../adapters/README.md) (NLP de détection).

## Limites connues

- `__init__.py` : export commenté référençant un symbole inexistant (`generate_embeddings`) — fossile d'API renommée, trompeur à la lecture ;
- chaîne morte résorbée (#2116 A1) : le maillon orphelin `embedding_pipeline` est retiré, le package est dormant-gardé (garde de capacité) ;
- aucun export effectif : tout import doit cibler `argumentation_analysis.nlp.embedding_utils` explicitement.
