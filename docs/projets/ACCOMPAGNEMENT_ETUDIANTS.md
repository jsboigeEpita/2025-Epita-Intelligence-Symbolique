# Accompagnement des Projets Étudiants - Argumentation Analysis

Bienvenue à tous les étudiants travaillant sur le projet "argumentation_analysis" !

Ce document a pour but de centraliser les informations utiles, les conseils, les problèmes connus et les ressources pour vous aider tout au long de votre projet.

## 1. Points d'Attention Généraux

*   **Configuration de l'environnement** : Assurez-vous d'avoir correctement configuré votre environnement Python, Java (JDK 11+), et JPype. Le notebook [`docs/resources/notebooks/Tweety.ipynb`](docs/resources/notebooks/Tweety.ipynb) (Partie 1) détaille les étapes.
*   **Utilisation de TweetyProject** : De nombreux sujets s'appuient sur TweetyProject. Familiarisez-vous avec :
    *   Le notebook principal : [`docs/resources/notebooks/Tweety.ipynb`](docs/resources/notebooks/Tweety.ipynb)
    *   Les exemples de code par projet : [`docs/projets/exemples_tweety_par_projet.md`](docs/projets/exemples_tweety_par_projet.md)
*   **Gestion de projet** : Pour les travaux en groupe, référez-vous aux conseils donnés dans le [message d'annonce](./message_annonce_etudiants.md#conseils-selon-la-taille-du-groupe). Utilisez GitHub (forks, branches, issues) efficacement.
*   **Livrables** : N'oubliez pas les livrables attendus (code, documentation, tests, rapport final) décrits dans le [message d'annonce](./message_annonce_etudiants.md#livrables-attendus).

## 2. Problèmes Connus et Pistes de Résolution

### 2.1 Problème d'import avec `org.tweetyproject.beliefdynamics.InformationObject` dans `Tweety.ipynb`

*   **Description** : Lors de l'exécution du notebook [`docs/resources/notebooks/Tweety.ipynb`](docs/resources/notebooks/Tweety.ipynb), un problème peut survenir lors du chargement de la classe `org.tweetyproject.beliefdynamics.InformationObject`. La JVM signale que la classe n'est pas trouvée, même si le JAR `org.tweetyproject.beliefdynamics-1.28-with-dependencies.jar` semble être correctement téléchargé et inclus dans le classpath.
*   **Impact** : Les cellules du notebook utilisant cette classe (notamment celles liées à la révision de croyances multi-agents, section 3.1 du notebook) et les projets étudiants s'appuyant sur le module `beliefdynamics` (ex: Projet 1.4.5) pourraient être affectés.
*   **Pistes de vérification/résolution** :
    1.  **Redémarrage du noyau** : Après le téléchargement des JARs (Cellule 7 du notebook), assurez-vous de bien redémarrer le noyau Jupyter (`Kernel -> Restart Kernel`) avant d'exécuter la cellule de démarrage de la JVM (Cellule 12).
    2.  **Vérification manuelle du JAR** :
        *   Assurez-vous que le fichier `libs/org.tweetyproject.beliefdynamics-1.28-with-dependencies.jar` existe et n'est pas corrompu (sa taille devrait être non nulle).
        *   Optionnel (avancé) : Vous pouvez essayer d'inspecter le contenu du JAR (c'est une archive zip) pour vérifier la présence du chemin `org/tweetyproject/beliefdynamics/InformationObject.class`.
    3.  **Classpath de la JVM** : Dans la sortie de la cellule 12 du notebook, vérifiez attentivement le classpath qui est passé à la JVM. Assurez-vous qu'il inclut le chemin absolu correct vers le JAR `beliefdynamics`.
    4.  **Version de JPype et Java** : Vérifiez que vous utilisez des versions compatibles de JPype, Python et Java JDK (11+ recommandé pour Tweety 1.28).
    5.  **Conflits potentiels** : Bien que les JARs "with-dependencies" soient censés minimiser cela, un conflit de dépendances très spécifique pourrait exister.
*   **Contournement temporaire (si le problème persiste)** : Si votre projet ne dépend pas directement de `InformationObject` mais d'autres parties de Tweety, vous pourrez peut-être commenter les sections problématiques du notebook pour continuer à utiliser le reste. Pour les projets affectés, une investigation plus poussée sera nécessaire.

### 2.2 Configuration des Outils Externes pour `Tweety.ipynb`

*   **Description** : Le notebook [`docs/resources/notebooks/Tweety.ipynb`](docs/resources/notebooks/Tweety.ipynb) utilise potentiellement des outils externes pour certaines fonctionnalités avancées (solveurs SAT, prouveurs FOL/ML, etc.). La configuration de ces outils est gérée dans les cellules 10 et 11 du notebook.
*   **Points d'attention** :
    1.  **Installation Manuelle** : Plusieurs outils comme EProver, et SPASS (sous Windows), nécessitent une installation manuelle sur votre système. Suivez les instructions sur leurs sites web respectifs. Clingo peut être détecté s'il est dans le PATH.
    2.  **Configuration des Chemins** : Après installation, vous devez indiquer les chemins d'accès corrects aux exécutables dans la variable `EXTERNAL_TOOLS` de la cellule 10 du notebook.
    3.  **Binaires Natifs Tweety** : Certains modules (comme ADF/SAT) utilisent des binaires natifs (`.dll`, `.so`, `.dylib`) que le notebook tente de télécharger dans `libs/native/`. Assurez-vous que le `java.library.path` est correctement configuré lors du démarrage de la JVM (Cellule 12) pour que Java trouve ces librairies.
    4.  **Messages d'erreur** : Lisez attentivement les sorties des cellules 10 et 11. Elles indiquent quels outils sont trouvés/configurés et lesquels posent problème. Si un outil externe n'est pas configuré, le notebook tentera d'utiliser des alternatives internes (souvent plus lentes) ou sautera les sections concernées.
*   **Conseils** :
    *   Si un projet spécifique requiert un outil externe, priorisez son installation et sa configuration.
    *   Pour les outils optionnels non requis par votre projet, vous pouvez ignorer leur configuration initiale.
    *   En cas de doute, référez-vous à la section 1.5 "Configuration des Outils Externes (Optionnel)" du notebook pour plus de détails sur chaque outil.

## 3. Bonnes Pratiques

*   **Communiquez** : N'hésitez pas à poser des questions à l'équipe pédagogique et à échanger avec les autres étudiants (via le forum de discussion mentionné).
*   **Documentez au fur et à mesure** : Une bonne documentation facilite la collaboration et la compréhension de votre travail.
*   **Testez régulièrement** : Écrivez des tests unitaires et d'intégration pour assurer la robustesse de votre code.
*   **Versionnez votre code** : Utilisez Git et GitHub de manière rigoureuse (commits fréquents, messages clairs, branches pour les fonctionnalités).

## 4. Liens Utiles (Rappel)

*   [Synthèse d'Accueil pour les Étudiants](./ACCUEIL_ETUDIANTS_SYNTHESE.md)
*   [Message d'annonce complet](./message_annonce_etudiants.md)
*   [Sujets de Projets Détaillés](./sujets_projets_detailles.md)
    *   [Fondements théoriques et techniques](./fondements_theoriques.md)
    *   [Développement système et infrastructure](./developpement_systeme.md)
    *   [Expérience utilisateur et applications](./experience_utilisateur.md)
*   [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md)
*   [Notebook principal Tweety.ipynb](../resources/notebooks/Tweety.ipynb)

Nous vous souhaitons un excellent projet !