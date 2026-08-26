# Compatibilité avec Python 3.12

## Problèmes connus

### JPype1
JPype1 1.4.1 n'est pas compatible avec Python 3.12 en raison de changements dans la structure interne de Python.
L'erreur spécifique est liée à la structure _longobject qui a changé dans Python 3.12.

### Solutions possibles

1. **Utiliser une version antérieure de Python (3.11 ou moins)** - C'est la solution la plus simple si vous avez besoin de JPype1.
2. **Utiliser pyjnius comme alternative** - pyjnius est une alternative à JPype1 qui peut fonctionner avec Python 3.12.
3. **Utiliser la version de développement de JPype1** - Vous pouvez essayer d'installer la dernière version de développement de JPype1 depuis GitHub.

## Autres dépendances

### numpy
numpy 2.0.0 ou supérieur est compatible avec Python 3.12 et peut être installé normalement.

## Comment appliquer ces correctifs

Le script `fix_dependencies_for_python312.ps1` a été retiré (#1803, étape 3) : sa logique
vit désormais dans l'outil unifié, dont la cascade `aggressive` installe numpy puis tente
JPype1 et ses solutions de repli.

```bash
python -m project_core.core_from_scripts.project_setup fix-deps --package numpy --package jpype1 --strategy aggressive
```

Si vous avez besoin de JPype1 spécifiquement, nous vous recommandons d'utiliser Python 3.11 ou une version antérieure.
