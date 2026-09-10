# `service_setup/` — initialisation des services d'analyse (avec un bug latent majeur)

## Rôle et frontière

Un seul module : `analysis_services.py` — `initialize_analysis_services()` construit le dict de services (JVM, LLM) consommé par le pipeline d'analyse.

N'est **pas** le montage de services réel de l'orchestration moderne (`orchestration/service_manager.py`, `OrchestrationServiceManager`) : ce module est la variante historique utilisée par `pipelines/analysis_pipeline.py`.

## Composants publics

`initialize_analysis_services(config: Dict | None = None) -> Dict[str, Any]` (`analysis_services.py:28`) — `load_dotenv(find_dotenv())` (:32), puis :

1. JVM (`settings.enable_jvm`, priorité config passée, :44+) — `services["jvm_ready"]` ;
2. service LLM : `create_llm_service(service_id="default_llm_service", model_id=settings.default_model_id, force_mock=settings.use_mock_llm)` (:65-69) ; `services["llm_service"]` (:71).

## Points d'entrée valides

Un importeur : [`pipelines/analysis_pipeline.py:38`](../pipelines/analysis_pipeline.py) — chaîne active : analysis_pipeline ← `pipelines/unified_text_analysis.py:77` ← `core/argumentation_analyzer.py:14`.

## Amont / aval

- Amont : `config.settings` (AppSettings), `create_llm_service`, initialisation JVM.
- Aval : `pipelines/analysis_pipeline.py` (services d'analyse).

## Statut d'intégration

**actif (transitif)** — importé par la chaîne pipelines ci-dessus. **Mais** en exécution réelle (non-mock), le service LLM échoue systématiquement (voir Limites) : le statut « actif » du module ne vaut pas « fonctionnel au LLM réel ».

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

- **Bug latent majeur** : `:68` `model_id=settings.default_model_id` — `AppSettings` n'a **pas** d'attribut `default_model_id` (`hasattr(AppSettings(), 'default_model_id') == False`, vérifié live ; l'attribut réel est `settings.service_manager.default_model_id`, valeur p.ex. `"gpt-5.6-luna"`). L'`AttributeError` est avalée par le handler `:82-86` (`logging.critical` puis `services["llm_service"] = None`) : **en mode réel (non-mock), le service LLM est systématiquement None** — seule la mock-mask route le masque ;
- contraste : [`kernel/kernel_builder.py:28`](../kernel/README.md) et `core/bootstrap.py:618` utilisent les attributs corrects (`chat_model_id`) — ce module est le seul chemin à lire l'attribut fantôme ;
- `logging.critical(..., exc_info=True)` sur un échec qui se produit à **chaque** run réel — un bruit de log critique permanent déguisé en configuration normale.
