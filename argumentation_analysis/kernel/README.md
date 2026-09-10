# `kernel/` — constructeur de kernel Semantic Kernel (outillage de tests)

## Rôle et frontière

Un seul module utile : `kernel_builder.py` (49 lignes) — `KernelBuilder.create_kernel(settings)` construit un `sk.Kernel` avec exactement **un** service chat (OpenAI ou Azure). `__init__.py` vide (0 octet).

N'est **pas** le chemin de construction du kernel en production : le kernel réel est assemblé par `core/bootstrap.py` (qui, au chemin direct :618, lit `settings.openai.chat_model_id` — l'attribut correct) ; ce builder n'est consommé **que par l'outillage de tests**.

## Composants publics

`KernelBuilder.create_kernel(settings: AppSettings) -> sk.Kernel` (`kernel_builder.py:18`, staticmethod) — dispatch sur `settings.service_manager.default_llm_service_id` (:22) :

- `"openai"` : `OpenAIChatCompletion(service_id="openai", ai_model_id=settings.openai.chat_model_id, api_key=…)` (:26-30) ; `ValueError` si clé absente (:32) ;
- `"azure"` : `AzureChatCompletion(deployment_name/endpoint/api_key depuis settings.azure_openai)` (:35-40) ; `ValueError` (:42-44) ;
- sinon : `ValueError` (:46).

## Points d'entrée valides

**Aucun importeur production.** Deux consommateurs, tous deux outillage de tests :

- [`tests/utils/scenario_runner.py:8,42`](../../tests/utils/scenario_runner.py) — `KernelBuilder.create_kernel(settings)` ;
- [`tests/integration/workers/worker_logic_puzzles_hardening.py:19,56`](../../tests/integration/workers/worker_logic_puzzles_hardening.py) — idem.

## Amont / aval

- Amont : `semantic_kernel`, `config.settings.AppSettings`.
- Aval : scenarios de tests d'intégration (scenario_runner).

## Statut d'intégration

**spécialisé (outillage de tests)** — résiduel côté production, vivant côté outillage : le scenario_runner sert les tests d'intégration workers.

## Artefacts et lecteurs

Aucun — kernel en mémoire.

## Tests représentatifs

`tests/kernel/test_kernel_builder.py` — **fichier vide (0 octet)** : le test dédié n'a jamais été écrit. Le module n'a **aucun test propre** ; il n'est exécuté qu'indirectement par les scenarios consommateurs (`tests/utils/scenario_runner.py`).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `kernel/`. Frère fonctionnel : [`core/bootstrap.py`](../core/README.md) (chemin production), [`integrations/`](../integrations/README.md) (doublon résiduel).

## Limites connues

- **Branche azure structurellement cassée** : `settings.azure_openai` (:34, :37-39) n'existe pas sur `AppSettings` actuel (`hasattr(AppSettings(), 'azure_openai') == False`, vérifié live) → `AttributeError` latent si le service global est réglé sur `"azure"` ; contraste avec la branche openai qui utilise l'attribut correct (`chat_model_id` :28) ;
- `tests/kernel/test_kernel_builder.py` vide (0 octet) — placeholder jamais rempli ;
- `__init__.py` vide : le package n'exporte rien, l'import doit cibler `kernel_builder` explicitement.
