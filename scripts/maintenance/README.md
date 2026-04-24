# Scripts de Maintenance

Scripts utilisés pour la maintenance du code, la structure du projet, la gestion des imports et des chemins, et l'intégrité des fichiers de configuration.

Les scripts de maintenance documentation, récupération et analyse se trouvent dans [`tools/`](tools/README.md).

## Scripts (ce répertoire)

### Commits & archéologie git
- `clean_commit_diffs.py` : nettoyage des diffs dans le cache des commits
- `enrich_commit_docs.py` : enrichit la documentation des commits
- `fix_missing_diffs.py` : répare les diffs manquants dans le cache
- `git_archeology_analyzer.py` : analyse archéologique d'un dépôt git
- `migrate_commit_cache.py` : migration du cache des commits vers un nouveau schéma
- `repair_commit_json.py` : répare les fichiers JSON du cache commits

### Tests & imports
- `test_imports.py` : test générique des imports du projet
- `test_imports_after_reorg.py` : test des imports après réorganisation
- `test_oracle_enhanced_compatibility.py` : vérifie la compatibilité Oracle Enhanced

### Documentation & rapports
- `clean_orphan_reports.py` : supprime les rapports orphelins
- `docs.py` : utilitaires génération docs
- `quarantine_orphan_audits.py` : met en quarantaine les audits orphelins

### Connectivité
- `validate_openai_connection.py` : vérifie la connectivité OpenAI

## Sous-répertoires

- [`tools/`](tools/README.md) — Documentation, récupération, analyse (17 scripts)
- `cleanup/` — Scripts one-shot de nettoyage historique
- `migration/` — Scripts one-shot de migration
- `recovered/` — Code récupéré lors de migrations passées
