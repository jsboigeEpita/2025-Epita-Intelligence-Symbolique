# Package Scripts
Parent : [`argumentation_analysis/README.md`](../README.md).

Points d'entrée **en ligne de commande** pour la maintenance des extraits
sources : réparation des marqueurs de début corrompus, vérification LLM de la
qualité des extraits, et un harnais de performance pour l'agent informel. Ce
sont des enveloppes minces — arguments, puis délégation à la logique des
packages voisins. Leur contrat est la ligne de commande, **pas une API** :
aucun module de production ne les importe (mesuré le 2026-10-08 sur `f79a7c089`).

## Contenu

| Fichier | Rôle | Délègue à |
|---|---|---|
| [`run_fix_missing_first_letter.py`](./run_fix_missing_first_letter.py) | répare les marqueurs de début corrompus, écrit un rapport | [`utils/extract_repair/fix_missing_first_letter.py`](../utils/extract_repair/fix_missing_first_letter.py) |
| [`run_verify_extracts_llm.py`](./run_verify_extracts_llm.py) | vérifie la qualité des extraits via un LLM | [`utils/extract_repair/verify_extracts_with_llm.py`](../utils/extract_repair/verify_extracts_with_llm.py) |
| [`test_performance_extraits.py`](./test_performance_extraits.py) | harnais pytest de performance de l'agent informel (`StateManagerMock`) | agent informel (kernel réel) |
| [`conftest.py`](./conftest.py) | fixtures pytest du répertoire — construit le kernel des tests ci-dessus | `UnifiedConfig` |
| [`__init__.py`](./__init__.py) | marque le paquet | — |

## Points d'entrée

### run_fix_missing_first_letter.py

```bash
python -m argumentation_analysis.scripts.run_fix_missing_first_letter \
    --input <extract_sources.json> --output <sortie.json> --report
```

Options : `--input/-i` (le défaut est un chemin absolu propre à un poste de
développement — passez le vôtre), `--output/-o` (sans lui, écrase l'entrée),
`--report/-r`, `--verbose/-v`.

### run_verify_extracts_llm.py

```bash
python -m argumentation_analysis.scripts.run_verify_extracts_llm \
    --output verify_extracts_llm_report.html --limit 5
```

Options : `--output/-o` (défaut `verify_extracts_llm_report_unencrypted.html`),
`--single-orator-only` (un alias déprécié reste parsé), `--only-source-index N`
(répétable, 0-based), `--limit/-l`, `--input/-i`, `--verbose/-v`.

### test_performance_extraits.py

```bash
pytest argumentation_analysis/scripts/test_performance_extraits.py
```

## État d'intégration

- **Actif, hors production.** Les scripts ne sont appelés par aucun module de
  production ni par une phase de workflow : ce sont des outils de maintenance
  lancés à la main. Preuve : aucune importation hors du paquet.
- **Payant, donc hors du gate CI.** `run_verify_extracts_llm.py` et les tests du
  répertoire construisent un kernel LLM réel
  (`UnifiedConfig(use_authentic_llm=True)`) : leurs *exécutions* consomment des
  jetons et ne tournent pas au gate (`requires_api`). C'est le résidu de
  l'item 6 de l'Epic #2088, porté par ses issues gatées #2936 / #2932.
- **Gratuit et vérifié.** Les exemples de commandes ci-dessus sont vérifiés
  sans réseau (résolution de module, aucun import) par
  `tests/unit/docs/test_readme_examples_execute_2088.py`.

## Scripts retirés

`repair_extract_markers.py` et `verify_extracts.py` ont vécu dans ce
répertoire. Leur logique a été déplacée :

- vers [`utils/dev_tools/repair_utils.py`](../utils/dev_tools/repair_utils.py)
  (voir ses commentaires « Fonctions déplacées depuis
  `argumentation_analysis/scripts/repair_extract_markers.py` ») ;
- remplacé par [`run_verify_extracts_llm.py`](./run_verify_extracts_llm.py)
  (voir le commentaire de renvoi dans
  [`utils/extract_repair/verify_extracts_with_llm.py`](../utils/extract_repair/verify_extracts_with_llm.py)).

Les noms de modules `argumentation_analysis.scripts.repair_extract_markers` et
`argumentation_analysis.scripts.verify_extracts` ne résolvent plus rien ;
aucune commande de ce README ne les cite.
