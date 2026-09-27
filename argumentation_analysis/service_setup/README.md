# `service_setup/` — initialisation des services d'analyse

## Rôle et frontière

Un seul module : `analysis_services.py` — `initialize_analysis_services()` construit le dict de services (JVM, LLM) consommé par le pipeline d'analyse.

N'est **pas** le montage de services réel de l'orchestration moderne (`orchestration/service_manager.py`, `OrchestrationServiceManager`) : ce module est la variante historique utilisée par `pipelines/analysis_pipeline.py`.

## Composants publics

`initialize_analysis_services(config: Dict | None = None) -> Dict[str, Any]` (`analysis_services.py:28`) — `load_dotenv(find_dotenv())` (:32), puis :

1. JVM (`settings.enable_jvm`, priorité config passée, :44+) — `services["jvm_ready"]` ;
2. service LLM : `create_llm_service(service_id="default_llm_service", force_mock=settings.use_mock_llm)` — pas de `model_id`, la fabrique résout (#2728) ; `services["llm_service"]`.

## Points d'entrée valides

Un importeur : [`pipelines/analysis_pipeline.py:38`](../pipelines/analysis_pipeline.py) — chaîne active : analysis_pipeline ← `pipelines/unified_text_analysis.py:77` ← `core/argumentation_analyzer.py:14`.

## Amont / aval

- Amont : `config.settings` (AppSettings), `create_llm_service`, initialisation JVM.
- Aval : `pipelines/analysis_pipeline.py` (services d'analyse).

## Statut d'intégration

**actif (transitif)** — importé par la chaîne pipelines ci-dessus.

## Artefacts et lecteurs

Aucun — dict en mémoire.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/pipelines/ -k "analysis_services or service_setup" -v
```

(coverage via la suite pipelines consommatrice ; vérifier les sélections disponibles localement).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `service_setup/`. Frère fonctionnel : [`orchestration/service_manager.py`](../orchestration/README.md) (montage moderne), [`core/bootstrap.py`](../core/README.md).

## Limites connues

- **Réparé par #2115** (`d24cb83a3`) : ce module lisait `settings.default_model_id`, un attribut qu'`AppSettings` ne porte pas. L'`AttributeError`, avalée par le handler (`logging.critical` puis `services["llm_service"] = None`), privait **chaque** run réel de son service LLM.
- **Réparé par #2728** : le site passait ensuite `model_id=settings.service_manager.default_model_id` — un champ qu'aucun résolveur ne lit — si bien qu'un poste qui fixe `OPENAI_CHAT_MODEL_ID` à un autre modèle ne le voyait pas appliqué ici. Le site ne passe plus de `model_id` : la fabrique résout depuis la même source que le résolveur (#2352), et le champ `ServiceManagerSettings.default_model_id` est retiré avec son dernier lecteur.
- Le handler de :84-88 transforme toujours tout échec de la fabrique en `services["llm_service"] = None`.
