# Notebooks de Référence pour l'Intelligence Symbolique

Ce répertoire contient des notebooks Jupyter de référence pour les projets d'Intelligence Symbolique.

## Tweety.ipynb

### Description

Le notebook `Tweety.ipynb` est un tutoriel complet sur la bibliothèque Java [TweetyProject](https://tweetyproject.org/) pour l'intelligence artificielle symbolique. Il se concentre particulièrement sur :

- La représentation de connaissances en logique
- L'argumentation computationnelle
- L'utilisation de JPype pour interfacer Python avec les classes Java de Tweety

Ce notebook est une ressource précieuse pour les étudiants travaillant sur des projets impliquant :
- La logique propositionnelle, du premier ordre, de description, modale, etc.
- Les cadres d'argumentation (Dung, ASPIC+, DeLP, ABA, etc.)
- La révision de croyances et l'analyse d'incohérence
- Les formalismes d'argumentation avancés (ADF, bipolaires, pondérés, etc.)

### Dépendances

Pour exécuter ce notebook, vous aurez besoin de :

1. **Python 3.x** (testé avec Python 3.10+)
2. **Java Development Kit (JDK)** version 11 ou supérieure
   - La variable d'environnement `JAVA_HOME` doit pointer vers le répertoire racine de votre installation JDK
   
3. **Packages Python** :
   - `jpype1` : Pour l'interface Python-Java
   - `requests` : Pour le téléchargement des fichiers
   - `tqdm` : Pour les barres de progression
   - `clingo` : Pour la programmation par ensemble réponse (ASP)

4. **Fichiers JAR de Tweety** :
   - Le notebook télécharge automatiquement les fichiers JAR nécessaires dans un sous-répertoire `libs/`
   - Le JAR principal est `tweety-full-1.28-with-dependencies.jar`
   - Plusieurs modules spécifiques sont également téléchargés

5. **Fichiers de données** :
   - Des exemples pour différentes logiques et formalismes d'argumentation sont téléchargés dans un sous-répertoire `resources/`

6. **Outils externes (optionnels)** :
   - Pour certaines fonctionnalités avancées, des outils externes peuvent être nécessaires :
     - Solveurs SAT (Lingeling, CaDiCaL, MiniSat, etc.)
     - Prouveurs FOL (EProver, SPASS)
     - Énumérateurs MUS (MARCO)
     - Solveurs MaxSAT (Open-WBO)
     - Solveurs ASP (Clingo)

### Structure des fichiers

Lors de l'exécution du notebook, la structure suivante est créée :

```
notebooks/
├── Tweety.ipynb           # Le notebook principal
├── libs/                  # Répertoire pour les fichiers JAR de Tweety
│   ├── tweety-full-1.28-with-dependencies.jar
│   ├── org.tweetyproject.arg.dung-1.28-with-dependencies.jar
│   ├── ...
│   └── native/            # Binaires natifs pour certains solveurs
├── resources/             # Fichiers de données d'exemple
│   ├── birds.txt          # Exemples DeLP
│   ├── example1.aba       # Exemples ABA
│   ├── ...
└── ext_tools/             # Outils externes (si configurés)
```

### Utilisation

1. Assurez-vous d'avoir installé les dépendances Python requises (`jpype1`, `requests`, `tqdm`, `clingo`)
2. Vérifiez que vous avez un JDK (version 11+) installé et que `JAVA_HOME` est correctement configuré
3. Exécutez le notebook cellule par cellule en suivant les instructions
4. Le notebook téléchargera automatiquement les fichiers JAR et les données nécessaires
5. Pour les fonctionnalités avancées, vous devrez peut-être configurer les chemins vers des outils externes

### Sections du notebook

Le notebook est organisé en 6 parties principales :

1. **Introduction et Configuration** : Installation des packages, téléchargement des JARs, démarrage de la JVM
2. **Logiques Fondamentales** : Propositionnelle, Premier Ordre, Description, Modale, etc.
3. **Révision de Croyances et Analyse d'Incohérence** : Révision multi-agents, mesures d'incohérence
4. **Argumentation Abstraite et Structurée** : Cadres de Dung, ASPIC+, DeLP, ABA, etc.
5. **Argumentation Avancée et Analyse** : ADF, frameworks bipolaires, pondérés, etc.
6. **Conclusion et Perspectives** : Récapitulatif et pistes d'exploration

Ce notebook constitue une ressource pédagogique complète pour explorer les différentes approches de l'intelligence artificielle symbolique à travers la bibliothèque TweetyProject.