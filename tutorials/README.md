# Tutoriels du Projet Intelligence Symbolique

Ce répertoire contient une série de tutoriels pour vous aider à prendre en main le système d'analyse argumentative et à comprendre ses fonctionnalités. Ces guides pratiques sont conçus pour accompagner les développeurs et utilisateurs à tous les niveaux d'expertise.

## Tutoriels Disponibles

### [01 - Prise en Main](./01_prise_en_main.md)
**Introduction au système d'analyse argumentative et configuration de l'environnement de développement.**

Ce tutoriel couvre :
- Installation des dépendances requises
- Configuration de l'environnement de développement
- Structure générale du projet
- Premier lancement du système
- Vérification de l'installation

**Prérequis :** Python 3.10+, pip, git

**Temps estimé :** 30 minutes

### [02 - Analyse de Discours Simple](./02_analyse_discours_simple.md)
**Guide pour effectuer une analyse de discours simple avec le système.**

Ce tutoriel couvre :
- Chargement d'un texte source
- Configuration des paramètres d'analyse
- Exécution d'une analyse basique
- Interprétation des résultats
- Exportation des résultats

**Prérequis :** Tutoriel 01 complété

**Temps estimé :** 45 minutes

### [03 - Analyse de Discours Complexe](./03_analyse_discours_complexe.md)
**Techniques avancées pour l'analyse de discours complexes, incluant la détection de sophismes et l'évaluation de la cohérence argumentative.**

Ce tutoriel couvre :
- Analyse de textes argumentatifs complexes
- Détection et classification des sophismes
- Évaluation de la cohérence argumentative
- Analyse des structures rhétoriques
- Génération de rapports détaillés

**Prérequis :** Tutoriels 01 et 02 complétés

**Temps estimé :** 1 heure

### [04 - Ajout d'un Nouvel Agent](./04_ajout_nouvel_agent.md)
**Instructions pour étendre le système avec un nouvel agent spécialiste.**

Ce tutoriel couvre :
- Architecture des agents dans le système
- Création d'un nouvel agent spécialiste
- Implémentation des méthodes requises
- Intégration avec le système existant
- Tests et validation du nouvel agent

**Prérequis :** Tutoriels 01, 02 et 03 complétés, connaissance de base en programmation orientée objet

**Temps estimé :** 2 heures

### [05 - Extension des Outils d'Analyse](./05_extension_outils_analyse.md)
**Guide pour développer et intégrer de nouveaux outils d'analyse rhétorique.**

Ce tutoriel couvre :
- Architecture des outils d'analyse
- Création d'un nouvel outil d'analyse
- Intégration avec les agents existants
- Optimisation des performances
- Tests et validation des résultats

**Prérequis :** Tutoriels 01 à 04 complétés, connaissance intermédiaire en Python

**Temps estimé :** 2-3 heures

## Progression Recommandée

Pour une prise en main optimale du système, nous vous recommandons de suivre les tutoriels dans l'ordre numérique :

1. Commencez par la [Prise en Main](./01_prise_en_main.md) pour configurer votre environnement
2. Passez ensuite à l'[Analyse de Discours Simple](./02_analyse_discours_simple.md) pour comprendre les bases
3. Approfondissez avec l'[Analyse de Discours Complexe](./03_analyse_discours_complexe.md)
4. Si vous souhaitez contribuer au système, explorez l'[Ajout d'un Nouvel Agent](./04_ajout_nouvel_agent.md)
5. Pour des fonctionnalités avancées, consultez l'[Extension des Outils d'Analyse](./05_extension_outils_analyse.md)

## Exemples Pratiques

Chaque tutoriel inclut des exemples pratiques que vous pouvez exécuter pour mieux comprendre les concepts présentés. Voici un exemple simple d'analyse de texte :

```python
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.models.extract_result import ExtractResult

# Initialiser le service d'extraction
extract_service = ExtractService()

# Analyser un texte simple
texte = "Ce texte contient un argument basé sur une autorité. Selon le Dr. Smith, expert reconnu, cette approche est la meilleure."
resultat = extract_service.analyze_text(texte)

# Afficher les résultats
print(f"Sophismes détectés : {resultat.fallacies}")
print(f"Structure argumentative : {resultat.structure}")
```

## Contribution aux Tutoriels

Nous encourageons les contributions pour améliorer ces tutoriels ou en ajouter de nouveaux. Pour contribuer :

1. **Identifiez un besoin** : Un sujet manquant, une explication à clarifier, ou un exemple à ajouter
2. **Créez une branche** : `git checkout -b amelioration-tutoriel`
3. **Rédigez votre contribution** : Suivez le format et le style des tutoriels existants
4. **Testez vos exemples** : Assurez-vous que tous les exemples fonctionnent correctement
5. **Soumettez une pull request** : Avec une description claire de votre contribution

## Ressources Complémentaires

- [Documentation du Projet](../docs/README.md)
- [Exemples d'Utilisation](../examples/README.md)
- [Guide du Développeur](../docs/guides/guide_developpeur.md)
- [API de Référence](../docs/reference/reference_api.md)
- [Outils d'Analyse Rhétorique](../docs/outils/README.md)

## Support et Questions

Si vous rencontrez des difficultés en suivant ces tutoriels ou si vous avez des questions :

1. Consultez la [documentation](../docs/README.md) pour des informations supplémentaires
2. Vérifiez les [problèmes connus](https://github.com/votre-organisation/votre-projet/issues) sur le dépôt GitHub
3. Posez vos questions dans la section [discussions](https://github.com/votre-organisation/votre-projet/discussions) du dépôt