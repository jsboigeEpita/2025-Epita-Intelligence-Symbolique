# `agents/tools/encryption/` — outillage Fernet du dataset chiffré (résiduel, exécution cassée)

## Rôle et frontière

4 scripts autonomes (`#!/usr/bin/env python`, `main()` + garde `__main__`), sans `__init__.py` — ce ne sont pas des modules importés mais des outils opérationnels historiques de création/inspection du dataset chiffré `data/extract_sources.json.gz.enc` :

- `create_complete_encrypted_config.py` (187 l.) — `encrypt_data` :45, `create_complete_encrypted_config` :58 : construit le bundle gzip+Fernet sources+config ;
- `create_and_archive_encrypted_config.py` (202 l.) — `main` :34 : orchestre création → vérification → archivage ;
- `inspect_encrypted_file.py` (146 l.) — `decrypt_data` :23, `inspect_encrypted_file` :39 ;
- `verify_encrypted_config.py` (134 l.) — `verify_encrypted_config` :38.

## Composants publics

Les fonctions `main`/métier ci-dessus. Aucun importeur nulle part (production **et** tests, grep plein dépôt).

## Points d'entrée valides

**Aucun** — exécution manuelle historique (`python <script>.py` ; chaque script fait un hack `sys.path` :17-20 pour s'auto-localiser). Trois casses mesurées/constatées empêchent aujourd'hui cette exécution (cf. Statut et Limites) ; le chemin opérationnel actuel du dataset passe par `argumentation_analysis/core/io_manager.py` et `scripts/security/` (p.ex. `verify_encrypted_dataset_completeness.py`).

## Amont / aval

- Amont (imports) : `config.settings`, `ui.config` (`ENCRYPTION_KEY` :41, `CONFIG_FILE_ENC` :61), `ui.utils`, `services/crypto_service`, `services/definition_service`, `models/extract_definition`.
- Aval : personne. Cible d'écriture : `data/extract_sources.json.gz.enc`.

## Statut d'intégration

**résiduel** — zéro importeur, zéro test, exécution cassée sur deux axes mesurés :

1. `create_and_archive_encrypted_config.py:31` importe `load_complete_encrypted_config` — **module inexistant** dans tout le dépôt (script non exécutable tel quel) ;
2. chaîne de clé morte : les scripts lisent `ui.config.ENCRYPTION_KEY`, qui vaut **`None`** même avec `.env` chargé (mesuré) — `ui.config:41` lit `settings.encryption_key`, alias de la variable d'environnement `ENCRYPTION_KEY` (`config/settings.py:178`), absente du `.env` canonique qui ne définit que la passphrase ; or les messages d'erreur des 4 scripts pointent `TEXT_CONFIG_PASSPHRASE` (p.ex. `create_complete_encrypted_config.py:63`) — mauvaise variable.

## Artefacts et lecteurs

`README_encryption_system.md` (suivi git) — documente 4 scripts **absents** du répertoire (`load_complete_encrypted_config.py`, `cleanup_after_encryption.py`, un générateur de cache nommé d'après une source réelle, et `deploy_and_run_scripts.ps1` — ce dernier vit à `agents/deploy_and_run_scripts.ps1`). Fossile + signal privacy (cf. Limites).

## Tests représentatifs

Aucun (aucun test n'importe ni n'exécute ces scripts).

## Frères et parent

Parent : [`../README.md`](../README.md). Remplacé fonctionnellement par : `core/io_manager.py` (chargement in-memory), `scripts/security/verify_encrypted_dataset_completeness.py`.

## Limites connues

- cible morte : `create_complete_encrypted_config.py:30-36` vise `utils/extract_repair/docs/extract_sources_updated.json`, fichier absent (garde :68-72 avorterait) ;
- **privacy** : `README_encryption_system.md:22` (suivi git) nomme une source réelle du dataset — signalé au coordinateur en canal privé pour arbitrage (le nom ne sera pas répété sur les surfaces GitHub) ;
- rien de tout cela n'est corrigeable dans une PR docs (mandat #2088) — anomalies portées en issues séparées.
