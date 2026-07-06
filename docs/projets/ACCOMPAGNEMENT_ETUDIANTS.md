# Accompagnement des Projets Étudiants - Argumentation Analysis

Bienvenue à tous les étudiants travaillant sur le projet "argumentation_analysis" !

Ce document a pour but de centraliser les informations utiles, les conseils, les problèmes connus et les ressources pour vous aider tout au long de votre projet.

## 1. Points d'Attention Généraux

*   **Configuration de l'environnement** : Assurez-vous d'avoir correctement configuré votre environnement Python, Java (JDK 11+), et JPype. Le notebook Tweety (Partie 1) — situé dans le dossier du cours `D:/CoursIA/MyIA.AI.Notebooks/SymbolicAI/Tweety/` — détaille les étapes. Pour des exemples de scripts d'initialisation, voir le répertoire [`scripts/`](../../scripts/) (l'ancien sous-dossier `scripts/execution/` a été consolidé dans `scripts/` ; [`scripts/testing/`](../../scripts/testing/) reste disponible séparément).
*   **Utilisation de TweetyProject** : De nombreux sujets s'appuient sur TweetyProject. Familiarisez-vous avec :
    *   Le notebook principal : Tweety (voir `D:/CoursIA/MyIA.AI.Notebooks/SymbolicAI/Tweety/`)
    *   Les exemples de code par projet : [`exemples_tweety_par_projet.md`](./exemples_tweety_par_projet.md)
*   **Gestion de projet** : Pour les travaux en groupe, référez-vous aux conseils donnés dans le [message d'annonce](./message_annonce_etudiants.md#conseils-selon-la-taille-du-groupe). Utilisez GitHub (forks, branches, issues) efficacement.
*   **Livrables** : N'oubliez pas les livrables attendus (code, documentation, tests, rapport final) décrits dans le [message d'annonce](./message_annonce_etudiants.md#livrables-attendus). Vous trouverez des exemples concrets de tests unitaires dans [`tests/unit/`](../../tests/unit/) (par exemple, [`tests/unit/argumentation_analysis/utils/core_utils/test_file_utils.py`](../../tests/unit/argumentation_analysis/utils/core_utils/test_file_utils.py)) et de tests d'intégration dans [`tests/integration/`](../../tests/integration/) (par exemple, [`tests/integration/test_logic_agents_integration.py`](../../tests/integration/test_logic_agents_integration.py)) qui peuvent vous servir de modèle et d'inspiration.

## 2. Problèmes Connus et Pistes de Résolution

### 2.1 Problème d'import avec `org.tweetyproject.beliefdynamics.InformationObject` dans `Tweety.ipynb`

*   **Description** : Lors de l'exécution du notebook Tweety (`D:/CoursIA/MyIA.AI.Notebooks/SymbolicAI/Tweety/`), un problème peut survenir lors du chargement de la classe `org.tweetyproject.beliefdynamics.InformationObject`. La JVM signale que la classe n'est pas trouvée, même si le JAR `org.tweetyproject.beliefdynamics-1.28-with-dependencies.jar` semble être correctement téléchargé et inclus dans le classpath.
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

*   **Description** : Le notebook Tweety (`D:/CoursIA/MyIA.AI.Notebooks/SymbolicAI/Tweety/`) utilise potentiellement des outils externes pour certaines fonctionnalités avancées (solveurs SAT, prouveurs FOL/ML, etc.). La configuration de ces outils est gérée dans les cellules 10 et 11 du notebook.
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
    *   Vous trouverez l'ensemble des tests unitaires dans le répertoire [`tests/unit/`](../../tests/unit/) et les tests d'intégration dans [`tests/integration/`](../../tests/integration/).
    *   Par exemple, pour comprendre comment tester des utilitaires de fichiers, consultez le test unitaire [`tests/unit/argumentation_analysis/utils/core_utils/test_file_utils.py`](../../tests/unit/argumentation_analysis/utils/core_utils/test_file_utils.py).
    *   Pour des exemples de tests d'intégration, notamment pour les agents logiques, explorez [`tests/integration/test_logic_agents_integration.py`](../../tests/integration/test_logic_agents_integration.py). Le répertoire [`tests/integration/jpype_tweety/`](../../tests/integration/jpype_tweety/) contient également des tests pertinents pour l'interaction avec Tweety via JPype.
    *   Des scripts d'exécution et de test plus généraux, pouvant servir d'exemples ou d'outils, sont disponibles dans [`scripts/`](../../scripts/) (les anciens sous-dossiers `scripts/execution/` et `scripts/testing/` ont été consolidés).
    *   Les notebooks Jupyter dans [`examples/notebooks/`](../../examples/notebooks/) peuvent aussi illustrer l'utilisation et le test de certaines fonctionnalités.
    *   De même, les scripts Python dans [`examples/`](../../examples/) offrent des cas d'usage concrets.
    *   N'oubliez pas les données d'exemple (référencées par certains tests et exemples) — la structure d'exemples changeant fréquemment, voir [`examples/`](../../examples/) pour les jeux de données disponibles.
*   **Versionnez votre code** : Utilisez Git et GitHub de manière rigoureuse (commits fréquents, messages clairs, branches pour les fonctionnalités).

## 4. Liens Utiles (Rappel)

*   [Synthèse d'Accueil pour les Étudiants](./ACCUEIL_ETUDIANTS_SYNTHESE.md)
*   [Message d'annonce complet](./message_annonce_etudiants.md)
*   [Sujets de Projets Détaillés](./sujets_projets_detailles.md)
    *   [Fondements théoriques et techniques](./fondements_theoriques.md)
    *   [Développement système et infrastructure](./developpement_systeme.md)
    *   [Expérience utilisateur et applications](./experience_utilisateur.md)
*   [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md)
*   Notebook principal Tweety (voir `D:/CoursIA/MyIA.AI.Notebooks/SymbolicAI/Tweety/`)

Nous vous souhaitons un excellent projet !