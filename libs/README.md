# Bibliothèques Externes

Ce répertoire contient les bibliothèques externes utilisées par le système d'analyse argumentative.

## Structure du Répertoire

### [Bibliothèques Natives](./native/)
Ce sous-répertoire contient les bibliothèques natives (DLL) nécessaires pour certaines fonctionnalités :
- **lingeling.dll** : Solveur SAT Lingeling utilisé pour la résolution de problèmes de satisfiabilité
- **minisat.dll** : Solveur SAT MiniSat utilisé pour la résolution de problèmes de satisfiabilité
- **picosat.dll** : Solveur SAT PicoSAT utilisé pour la résolution de problèmes de satisfiabilité

### Bibliothèques Java (JAR)
Le répertoire principal contient les bibliothèques Java du projet Tweety, utilisées pour l'analyse argumentative formelle :

#### Bibliothèques Principales
- **org.tweetyproject.tweety-full-1.28-with-dependencies.jar** : Package complet de Tweety avec toutes les dépendances
- **org.tweetyproject.commons-1.28-with-dependencies.jar** : Fonctionnalités communes de Tweety
- **org.tweetyproject.math-1.28-with-dependencies.jar** : Fonctionnalités mathématiques de Tweety

#### Bibliothèques d'Argumentation
- **org.tweetyproject.arg.dung-1.28-with-dependencies.jar** : Implémentation des cadres d'argumentation de Dung
- **org.tweetyproject.arg.aspic-1.28-with-dependencies.jar** : Implémentation du framework ASPIC+
- **org.tweetyproject.arg.aba-1.28-with-dependencies.jar** : Implémentation de l'argumentation basée sur les hypothèses (ABA)
- **org.tweetyproject.arg.bipolar-1.28-with-dependencies.jar** : Implémentation des cadres d'argumentation bipolaires
- **org.tweetyproject.arg.deductive-1.28-with-dependencies.jar** : Implémentation de l'argumentation déductive
- **org.tweetyproject.arg.rankings-1.28-with-dependencies.jar** : Implémentation des classements d'arguments

#### Bibliothèques de Logique
- **org.tweetyproject.logics.pl-1.28-with-dependencies.jar** : Implémentation de la logique propositionnelle
- **org.tweetyproject.logics.fol-1.28-with-dependencies.jar** : Implémentation de la logique du premier ordre
- **org.tweetyproject.logics.ml-1.28-with-dependencies.jar** : Implémentation de la logique modale
- **org.tweetyproject.logics.pcl-1.28-with-dependencies.jar** : Implémentation de la logique probabiliste conditionnelle

## Utilisation

Ces bibliothèques sont utilisées par le système via l'interface JVM fournie par JPype. Pour plus d'informations sur l'intégration avec Tweety, consultez la documentation du [JVM Service](../argumentation_analysis/services/README.md).

### Chargement des Bibliothèques Natives

Les bibliothèques natives sont chargées automatiquement par le système lors de l'initialisation du service JVM. Assurez-vous que le chemin vers le répertoire `native` est correctement configuré dans les paramètres du système.

### Utilisation des Bibliothèques Java

Les bibliothèques Java sont utilisées via JPype pour accéder aux fonctionnalités de Tweety. Voici un exemple d'utilisation :

```python
from argumentation_analysis.services.jvm_service import JVMService

# Initialisation du service JVM
jvm_service = JVMService()
jvm_service.initialize()

# Utilisation de Tweety
pl_parser = jvm_service.get_class("org.tweetyproject.logics.pl.syntax.PlParser")()
formula = pl_parser.parseFormula("a && (b || c)")

# Nettoyage
jvm_service.shutdown()
```

## Mise à Jour des Bibliothèques

Pour mettre à jour les bibliothèques Tweety vers une nouvelle version :

1. Téléchargez les nouvelles versions des JAR depuis le [site officiel de Tweety](https://tweetyproject.org/download/)
2. Remplacez les fichiers JAR existants par les nouvelles versions
3. Mettez à jour les bibliothèques natives si nécessaire
4. Exécutez les tests pour vérifier la compatibilité

## Dépendances

- **Java JDK 11+** : Nécessaire pour exécuter les bibliothèques Java
- **JPype** : Utilisé pour l'interface entre Python et Java
- **Windows x64** : Les bibliothèques natives sont compilées pour Windows 64 bits

## Ressources Associées

- [Documentation Tweety](https://tweetyproject.org/doc/)
- [Service JVM](../argumentation_analysis/services/README.md)
- [Tests d'Intégration JVM](../argumentation_analysis/tests/test_jvm_example.py)