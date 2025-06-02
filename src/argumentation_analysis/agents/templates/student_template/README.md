# Template d'Agent pour Étudiants

Ce template fournit une structure de base pour créer un nouvel agent dans le système d'analyse d'argumentation.

## Structure du Template

- `__init__.py` - Fichier d'initialisation du module
- `agent.py` - Implémentation principale de l'agent
- `definitions.py` - Définitions des structures de données utilisées par l'agent
- `prompts.py` - Prompts utilisés pour les interactions avec les modèles de langage

## Comment Utiliser ce Template

1. **Copier le Template**
   - Copiez ce répertoire dans un nouvel emplacement
   - Renommez le répertoire selon le nom de votre agent

2. **Personnaliser les Fichiers**
   - Modifiez `agent.py` pour implémenter les fonctionnalités de votre agent
   - Adaptez `definitions.py` pour définir les structures de données nécessaires
   - Personnalisez `prompts.py` avec vos propres prompts

3. **Tester Votre Agent**
   - Créez des tests unitaires dans un répertoire `tests/`
   - Utilisez les scripts de test fournis dans `runners/test/`

4. **Intégrer Votre Agent**
   - Mettez à jour le système d'orchestration pour inclure votre agent
   - Testez l'intégration avec les autres agents

## Bonnes Pratiques

- Suivez les conventions de nommage existantes
- Documentez votre code avec des docstrings
- Écrivez des tests pour chaque fonctionnalité
- Gardez les responsabilités de votre agent bien définies
- Utilisez les services et utilitaires existants plutôt que de réinventer la roue