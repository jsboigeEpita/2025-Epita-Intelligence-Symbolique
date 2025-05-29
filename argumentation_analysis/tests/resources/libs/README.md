# JARs de test pour argumentation_analysis

Ce répertoire contient les JARs minimaux nécessaires pour exécuter les tests
qui dépendent de la JVM. Ces JARs sont une version réduite des JARs Tweety
utilisés par le projet.

## Contenu

- `org.tweetyproject.tweety-full-*.jar`: JAR principal de Tweety
- `org.tweetyproject.logics.pl-*.jar`: Module de logique propositionnelle
- `org.tweetyproject.commons-*.jar`: Module de base

## Utilisation

Ces JARs sont utilisés automatiquement par la classe `JVMTestCase` lorsque
des tests qui dépendent de la JVM sont exécutés.

## Mise à jour

Pour mettre à jour ces JARs, exécutez le script `scripts/download_test_jars.py`
avec l'option `--force`.
