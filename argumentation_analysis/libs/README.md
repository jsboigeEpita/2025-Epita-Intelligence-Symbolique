# Répertoire des bibliothèques externes

Ce répertoire contient les bibliothèques externes (JARs) nécessaires pour le projet d'analyse argumentative.

## Structure

- `libs/` : Contient les JARs Tweety principaux
  - `native/` : Contient les bibliothèques natives spécifiques à la plateforme

## Utilisation

Les JARs sont téléchargés automatiquement par la fonction `download_tweety_jars` dans le module `core.jvm_setup` lors de l'initialisation de la JVM.

## JARs requis

- `org.tweetyproject.tweety-full-*.jar` : JAR principal de Tweety
- Modules spécifiques (téléchargés automatiquement) :
  - `org.tweetyproject.logics.pl-*.jar` : Module de logique propositionnelle
  - `org.tweetyproject.arg.dung-*.jar` : Module d'argumentation de Dung
  - etc.

## Bibliothèques natives

Les bibliothèques natives dépendent de la plateforme :

- Windows : `*.dll`
- Linux : `*.so`
- macOS : `*.dylib`

## Note importante

Ce répertoire est créé et rempli dynamiquement. Les fichiers `.gitkeep` sont inclus pour s'assurer que la structure de répertoires est maintenue dans le dépôt Git.