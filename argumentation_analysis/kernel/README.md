# `kernel/` — constructeur de kernel Semantic Kernel (outillage de tests)

## Rôle et frontière

Un seul module utile : `kernel_builder.py` (49 lignes) — `KernelBuilder.create_kernel(settings)` construit un `sk.Kernel` avec exactement **un** service chat (OpenAI ou Azure). `__init__.py` vide (0 octet).

N'est **pas** le chemin de construction du kernel en production : le kernel réel est assemblé par `core/bootstrap.py` (qui, au chemin direct :618, lit `settings.openai.chat_model_id` — l'attribut correct) ; ce builder n'est consommé **que par l'outillage de tests**.

## Composants publics

`KernelBuilder.create_kernel(settings: AppSettings) -> sk.Kernel` (`kernel_builder.py:18`, staticmethod) — dispatch sur `settings.service_manager.default_llm_service_id` (:22) :

- `"openai"` : `OpenAIChatCompletion(service_id="openai", ai_model_id=settings.openai.chat_model_id, api_key=…)` (:26-30) ; `ValueError` si clé absente (:32) ;
- `"azure"` : `AzureChatCompletion(deployment_name/endpoint/api_key depuis settings.azure_openai)` (:40-47) ; `ValueError` (:48-51) ;
- sinon : `ValueError` (:46).

## Points d'entrée valides

**Aucun consommateur.** Ni importeur production, ni outillage de tests. Les deux derniers consommateurs, `tests/utils/scenario_runner.py` et `tests/integration/workers/worker_logic_puzzles_hardening.py`, passaient le noyau construit à `orchestration/orchestrator.py`, une coquille dont `run_analysis_async` levait `NotImplementedError`. #2700 a retiré le worker, #2703 le runner et la coquille. Le module n'est plus appelé que par ses propres tests.

## Amont / aval

- Amont : `semantic_kernel`, `config.settings.AppSettings`.
- Aval : aucun depuis #2703 (le dernier, `scenario_runner`, est retiré).

## Statut d'intégration

**résiduel** — aucun consommateur depuis #2703 ; seuls ses propres tests l'appellent. Le chemin production qui construit un noyau est [`core/bootstrap.py`](../core/README.md).

## Artefacts et lecteurs

Aucun — kernel en mémoire.

## Tests représentatifs

`tests/kernel/test_kernel_builder.py` — les 3 tests posés par #2115 (voir « Limites connues ») ; ce sont les seuls appels du module.

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `kernel/`. Frère fonctionnel : [`core/bootstrap.py`](../core/README.md) (chemin production), [`integrations/`](../integrations/README.md) (doublon résiduel).

## Limites connues

- **Branche azure — réparée, puis remise d'aplomb** : #2115 a corrigé le *lecteur* (il lisait `settings.azure_openai`, nom qu'`AppSettings` ne portait pas : `AttributeError` avalée en « clé absente », branche morte depuis sa naissance) ; #2198 a corrigé le *placement* — le bloc remonte de `JVMSettings` vers `AppSettings`, qui est la racine du défaut. Une seule orthographe subsiste (:40).
- `tests/kernel/test_kernel_builder.py` n'est plus un placeholder vide : #2115 y a posé 3 tests (branche azure atteint `AzureChatCompletion`, contrôle openai, provider inconnu nommé).
- `__init__.py` vide : le package n'exporte rien, l'import doit cibler `kernel_builder` explicitement.
