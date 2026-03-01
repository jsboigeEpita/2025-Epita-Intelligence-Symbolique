# Integration Plan: Index Semantique Arguments (Arg_Semantic_Index)

## 1. Sujet (resume spec)

**Spec** : `2.4.1_Index_Semantique_Arguments.md`

**Objectif** : Systeme d'indexation semantique et de recherche RAG pour les arguments, base sur Kernel Memory.

**Fonctionnalites demandees** :
- Upload et indexation de documents argumentatifs
- Recherche semantique par pertinence
- Question-answering RAG avec citation des sources
- Interface Streamlit

## 2. Travail Etudiant (analyse code)

### Structure (`Arg_Semantic_Index/`, ~230 LoC + UI)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `kernel_memory/km_client.py` | 115 | **Client HTTP** : 5 fonctions (upload, wait, ask, search, clean) |
| `UI_streamlit.py` | 113 | App Streamlit 2 tabs (search + Q&A) |
| `sources/` | — | Documents sources (JSON) |

### Points forts
- Client HTTP clean et fonctionnel
- `format_doc_id()` pour slugs ASCII-safe
- Retries sur ask/search
- UI Streamlit fonctionnelle

## 3. Etat Actuel dans le Tronc Commun

### Fichier existant

`argumentation_analysis/services/semantic_index_service.py` (323 LoC)

### Ce qui fonctionne

- **`SemanticIndexService`** : adaptateur CRUD complet pour Kernel Memory
- 4 operations : `upload_document()`, `wait_for_indexing()`, `search()`, `ask()`
- Dataclasses propres (`SearchResult`, `AskResult`)
- `format_doc_id()` identique au code etudiant
- Bearer auth support
- Configuration via constructeur ou env vars

### Ecarts

1. **ServiceDiscovery** pas effectivement enregistre
2. **CapabilityRegistry** pas effectivement enregistre

## 4. Plan de Consolidation

### 4.1 Classification : Service (verification/cablage)

L'adaptateur est le **mieux integre** de tous les projets. Il manque uniquement le cablage formel.

### 4.2 Actions

1. **Enregistrer dans ServiceDiscovery** comme provider `semantic_search`
2. **Enregistrer dans CapabilityRegistry** (type SERVICE)
3. **Verifier l'endpoint** (`KERNEL_MEMORY_URL`)

## 5. Criteres d'Acceptation

- [ ] Enregistre dans `ServiceDiscovery`
- [ ] Enregistre dans `CapabilityRegistry` (type SERVICE)
- [ ] `is_available()` fonctionne
- [ ] Tests passent
- [ ] Zero regression

## 6. Notes

### Effort estime : ~15min

Le code est excellent. Cablage formel uniquement.
