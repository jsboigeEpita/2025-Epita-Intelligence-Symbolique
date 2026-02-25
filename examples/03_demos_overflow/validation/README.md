# 🔍 Validation

## Description

Ce répertoire contient les démonstrations de validation exhaustive et de tests de qualité du système d'argumentation. Ces démos sont conçues pour vérifier le bon fonctionnement du système, valider l'intégrité des composants et produire des rapports de validation détaillés.

## Contenu

### Fichiers

| Fichier | Description | Niveau |
|---------|-------------|--------|
| [`validation_complete_epita.py`](./validation_complete_epita.py) | Validation complète du système avec bootstrap robuste et détection automatique de la racine projet | Avancé |
| [`validation_report.md`](./validation_report.md) | Rapport de validation consolidé avec métriques de performance et résultats | Documentation |

## Utilisation

### Validation Complète EPITA

Script principal de validation exhaustive du système :

```bash
# Exécution standard
python demos/validation/validation_complete_epita.py

# Depuis le répertoire demos/validation/
cd demos/validation
python validation_complete_epita.py
```

**Ce que ce script valide** :
- ✅ Configuration de l'environnement projet
- ✅ Chargement des modules core
- ✅ Initialisation des agents
- ✅ Fonctionnement des services d'analyse
- ✅ Intégrité des dépendances

### Validation Deep Taxonomy

Validation approfondie de la taxonomie des sophismes :

```bash
# La commande suivante est obsolète car le script a été supprimé.
# python demos/validation/validation_deep_taxonomy.py
```

**Ce que ce script valide** :
- ✅ Structure de la taxonomie des sophismes
- ✅ Cohérence des catégories et sous-catégories
- ✅ Complétude des définitions
- ✅ Exemples associés à chaque sophisme

### Rapport de Validation

Le rapport consolidé [`validation_report.md`](./validation_report.md) contient :
- 📊 Métriques de performance
- ✅ Résultats de validation
- 🐛 Bugs identifiés et corrigés
- 📈 Évolution de la qualité

## Dépendances

Ces scripts utilisent le pattern de bootstrap standard du projet :

```python
from pathlib import Path
import sys

current_file_path = Path(__file__).resolve()
project_root = next((p for p in current_file_path.parents if (p / "pyproject.toml").exists()), None)

if project_root is None:
    raise FileNotFoundError("Impossible de localiser la racine du projet")
    
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
from argumentation_analysis.core.environment import ensure_env
ensure_env()
```

Ce pattern garantit que :
- Le script fonctionne depuis n'importe quel emplacement
- L'environnement est correctement configuré
- Les imports relatifs fonctionnent correctement

## Notes

### Bonnes Pratiques de Validation

1. **Exécuter avant tout commit majeur** : Vérifiez que le système fonctionne après vos modifications
2. **Automatiser les validations** : Intégrez ces scripts dans votre CI/CD
3. **Consulter le rapport** : Utilisez `validation_report.md` comme référence de qualité
4. **Isoler les problèmes** : Si une validation échoue, utilisez les outils de debugging

### Pattern Bootstrap Recommandé

Tous les scripts de validation utilisent le **circuit d'environnement robuste** qui :
- Détecte automatiquement la racine du projet via `pyproject.toml`
- Gère les cas où le script est appelé directement ou déplacé
- Remonte l'arborescence jusqu'à trouver la racine
- Configure `sys.path` avant tout import projet
- Appelle `ensure_env()` pour garantir la configuration complète

Ce pattern est **recommandé pour tous vos scripts personnalisés**.

## Cas d'Usage

### Pour les Développeurs

Avant de pusher votre code :
```bash
# Validation rapide
python demos/validation/validation_complete_epita.py

# Si succès, procéder au commit
git add .
git commit -m "feat: votre fonctionnalité"
```

### Pour l'Intégration Continue

Dans votre workflow CI/CD :
```yaml
- name: Validation système
  run: python demos/validation/validation_complete_epita.py
  
- name: Validation taxonomie (obsolète)
  run: # python demos/validation/validation_deep_taxonomy.py
```

### Pour le Débogage

Si un test échoue, passez aux démos de debugging :
```bash
# Identifier le problème
python demos/debugging/debug_single_fallacy.py
```

## Ressources Connexes

- **[Debugging](../debugging/README.md)** : Outils de débogage ciblé
- **[Integration](../integration/README.md)** : Tests d'intégration
- **[Tests](../../tests/)** : Suite de tests automatisés complète
- **[Documentation](../../docs/)** : Référence technique

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA