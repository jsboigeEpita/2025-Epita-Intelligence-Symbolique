# Utilitaires d'Analyse d'Argumentation

Ce répertoire contient des modules utilitaires transverses utilisés par différents composants du projet d'analyse d'argumentation.

## Modules Disponibles

### `performance_monitoring.py`

Ce module fournit des outils pour monitorer la performance des fonctions critiques, notamment via des décorateurs et des gestionnaires de contexte.

#### Fonctionnalités principales

- **Décorateur `@monitor_performance`**: Un décorateur simple à utiliser pour mesurer le temps d'exécution d'une fonction. Il logue le résultat dans un fichier structuré.
- **Logging Structuré**: Les logs de performance sont écrits au format JSON dans `logs/oracle_performance.log`, ce qui facilite leur parsing et leur analyse par des outils externes.
- **Configuration Centralisée**: La configuration du logger (destination, format, niveau) est gérée de manière centralisée dans le module.

#### Comment l'utiliser

Pour monitorer une fonction, il suffit d'importer le décorateur et de l'appliquer à la définition de la fonction :

```python
from argumentation_analysis.utils.performance_monitoring import monitor_performance

@monitor_performance(log_args=True)
def ma_fonction_critique(param1, param2):
    # Logique métier à monitorer
    pass
```

L'argument `log_args=True` est optionnel et permet de capturer les arguments passés à la fonction dans les logs de performance.
