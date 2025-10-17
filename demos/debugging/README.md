# 🐛 Debugging

## Description

Ce répertoire contient les outils et démonstrations pour le débogage ciblé d'un sophisme ou d'une analyse spécifique. Ces outils permettent d'isoler et de diagnostiquer des problèmes précis dans le système d'argumentation.

## Contenu

### Fichiers

| Fichier | Description | Niveau |
|---------|-------------|--------|
| [`debug_single_fallacy.py`](./debug_single_fallacy.py) | Outil de débogage pour analyser un sophisme spécifique avec Semantic Kernel | Avancé |

## Utilisation

### Debug Single Fallacy

Outil pour déboguer l'analyse d'un sophisme spécifique :

```bash
# Exécution standard
python demos/debugging/debug_single_fallacy.py

# Depuis le répertoire demos/debugging/
cd demos/debugging
python debug_single_fallacy.py
```

**Ce que cet outil fait** :
- 🔍 Analyse détaillée d'un sophisme ciblé
- 📊 Affichage pas-à-pas du raisonnement
- 🔬 Inspection des résultats intermédiaires
- 📝 Logging verbeux pour diagnostic
- ⚡ Intégration avec Semantic Kernel

**Cas d'usage typiques** :
1. **Faux positif** : Identifier pourquoi un sophisme est détecté à tort
2. **Faux négatif** : Comprendre pourquoi un sophisme n'est pas détecté
3. **Performance** : Analyser les temps d'exécution
4. **Résultats inattendus** : Investiguer des résultats surprenants

## Workflow de Debugging

### 1. Identifier le Problème

```bash
# Exécuter une validation générale
python demos/validation/validation_complete_epita.py

# Si un problème est détecté, isoler le sophisme concerné
```

### 2. Déboguer le Sophisme

```python
# Exemple d'utilisation programmatique
from demos.debugging.debug_single_fallacy import debug_fallacy

# Déboguer un sophisme spécifique
result = debug_fallacy(
    text="Votre texte contenant le sophisme",
    fallacy_type="ad_hominem",
    verbose=True
)

print(result.diagnostic)
```

### 3. Analyser les Résultats

Le script produit :
- **Log détaillé** : Chaque étape de l'analyse
- **Résultats intermédiaires** : États du système
- **Métriques** : Temps d'exécution, confiance
- **Recommandations** : Actions correctives

## Dépendances

Ce script utilise :
- **Semantic Kernel** : Framework d'orchestration IA
- **asyncio** : Gestion asynchrone
- **json** : Sérialisation des résultats
- **re** : Parsing et extraction de patterns

Bootstrap standard :
```python
from pathlib import Path
import sys
import asyncio

current_file = Path(__file__).resolve()
project_root = next((p for p in current_file.parents if (p / "pyproject.toml").exists()), None)

if project_root and str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
from argumentation_analysis.core.environment import ensure_env
ensure_env()

import semantic_kernel as sk
```

## Techniques de Debugging

### Mode Verbose

Activer le mode verbose pour un logging détaillé :

```python
# Dans le script, modifier la configuration
DEBUG_MODE = True
VERBOSE_LOGGING = True
```

### Breakpoints Stratégiques

Points clés où ajouter des breakpoints :
1. **Après parsing** : Vérifier la structure du texte
2. **Pendant l'analyse** : Observer les inférences
3. **Avant agrégation** : Valider les résultats intermédiaires
4. **Après finalisation** : Examiner le résultat final

### Logging Structuré

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug("Debugging sophisme: %s", fallacy_type)
```

## Cas d'Usage

### Problème : Faux Positif

**Symptôme** : Le système détecte un sophisme qui n'existe pas

**Démarche** :
```bash
# 1. Isoler le texte problématique
python demos/debugging/debug_single_fallacy.py --text "texte problématique"

# 2. Analyser le raisonnement
# Observer où la détection se déclenche incorrectement

# 3. Ajuster les seuils ou la logique
# Modifier les paramètres de détection
```

### Problème : Faux Négatif

**Symptôme** : Un sophisme évident n'est pas détecté

**Démarche** :
```bash
# 1. Vérifier que le sophisme est dans la taxonomie
# python demos/validation/validation_deep_taxonomy.py (script obsolète)

# 2. Déboguer l'analyse
python demos/debugging/debug_single_fallacy.py --text "texte avec sophisme" --expected "type_sophisme"

# 3. Identifier le point de défaillance
# Le sophisme est-il reconnu mais filtré ?
# La confiance est-elle trop basse ?
```

### Problème : Performance

**Symptôme** : L'analyse est trop lente

**Démarche** :
```bash
# 1. Profile le script
python -m cProfile -o output.prof demos/debugging/debug_single_fallacy.py

# 2. Analyser le profil
python -m pstats output.prof

# 3. Identifier les bottlenecks
# Quelles fonctions prennent le plus de temps ?
```

## Configuration

### Variables d'Environnement

```bash
# Activer le mode debug
export DEBUG_FALLACY_ANALYZER=true

# Niveau de logging
export LOG_LEVEL=DEBUG

# Timeout pour l'analyse
export ANALYSIS_TIMEOUT=30
```

### Fichier de Configuration

Créer un fichier `debug_config.json` :
```json
{
  "verbose": true,
  "log_level": "DEBUG",
  "timeout_seconds": 30,
  "enable_profiling": true,
  "output_format": "detailed"
}
```

## Patterns de Debugging Avancés

### 1. Comparative Analysis

Comparer plusieurs versions d'analyse :
```python
results_v1 = analyze_with_version("v1.0", text)
results_v2 = analyze_with_version("v2.0", text)

diff = compare_results(results_v1, results_v2)
print(diff)
```

### 2. Minimal Reproduction

Réduire le texte au minimum pour reproduire le bug :
```python
original = "Long texte avec bug..."
minimal = find_minimal_reproduction(original, bug_detector)
print(f"Texte minimal: {minimal}")
```

### 3. Bisection Search

Trouver la commit qui a introduit le bug :
```bash
git bisect start
git bisect bad  # Le bug est présent
git bisect good v1.0  # Version connue sans bug

# Pour chaque commit
python demos/debugging/debug_single_fallacy.py
git bisect good/bad
```

## Ressources Connexes

- **[Validation](../validation/README.md)** : Tests de validation système
- **[Integration](../integration/README.md)** : Tests d'intégration
- **[Showcases](../showcases/README.md)** : Exemples d'usage simplifié
- **[Documentation](../../docs/)** : Référence technique

## Notes

### Limites Actuelles

⚠️ **Limitations connues** :
- Analyse synchrone uniquement (pas de streaming)
- Timeout fixe de 30 secondes
- Pas de cache des résultats intermédiaires
- Logging non persistant

### Améliorations Futures

💡 **Roadmap** :
- [ ] Support du streaming de résultats
- [ ] Cache intelligent des analyses
- [ ] Dashboard de monitoring en temps réel
- [ ] Intégration avec debugger Python (pdb)
- [ ] Export des traces au format standard

### Contribution

Pour améliorer les outils de debugging :
1. Identifier un cas de debugging manquant
2. Implémenter l'outil ou la fonctionnalité
3. Documenter l'usage
4. Soumettre une PR

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA