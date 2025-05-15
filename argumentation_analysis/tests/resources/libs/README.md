# JARs de test pour argumentation_analysis

Ce répertoire contient les JARs minimaux nécessaires pour exécuter les tests
qui dépendent de la JVM. Ces JARs sont une version réduite des JARs Tweety
utilisés par le projet.

## Contenu

- `org.tweetyproject.tweety-full-*.jar`: JAR principal de Tweety
- `org.tweetyproject.logics.pl-*.jar`: Module de logique propositionnelle
- `org.tweetyproject.commons-*.jar`: Module de base

## Structure

- `libs/` : Contient les JARs Tweety minimaux pour les tests
  - `native/` : Contient les bibliothèques natives spécifiques à la plateforme

## Utilisation

Ces JARs sont utilisés automatiquement par la classe `JVMTestCase` lorsque
des tests qui dépendent de la JVM sont exécutés. La classe `JVMTestCase` copie
ces JARs vers le répertoire `libs/` principal si nécessaire.

## Mise à jour

Pour télécharger ou mettre à jour ces JARs, exécutez le script :

```bash
python scripts/download_test_jars.py
```

Pour forcer le téléchargement même si les JARs existent déjà :

```bash
python scripts/download_test_jars.py --force
```

## Note importante

Ce répertoire est initialement vide dans le dépôt Git. Les JARs sont téléchargés
automatiquement lors de la première exécution des tests qui en ont besoin.