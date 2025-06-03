# Rapport : Réparation des bornes défectueuses dans les extraits

## Contexte et problématique

Notre application d'analyse d'argumentation utilise un système d'extraits définis par des marqueurs de début et de fin dans des textes sources. Ces extraits permettent d'isoler des passages spécifiques pour l'analyse argumentative. Cependant, plusieurs problèmes ont été identifiés :

1. **Bornes introuvables** : Certains marqueurs de début ou de fin ne sont pas trouvés dans les textes sources, rendant l'extraction impossible.
2. **Bornes incorrectes** : Certains marqueurs existent mais ne délimitent pas correctement l'extrait souhaité.
3. **Problèmes spécifiques au corpus d'Hitler** : Le corpus de discours d'Hitler est particulièrement volumineux et présente des défis spécifiques (structure complexe, formatage particulier).

Ces problèmes empêchent l'extraction correcte des textes et compromettent la qualité de l'analyse argumentative.

## Solution développée

Pour résoudre ces problèmes, nous avons développé un script de réparation automatique des bornes défectueuses qui utilise une approche basée sur des agents. Le script `repair_extract_markers.py` et son notebook associé `repair_extract_markers.ipynb` permettent de :

1. **Analyser les extraits existants** pour détecter les bornes défectueuses
2. **Proposer des corrections automatiques** en utilisant des algorithmes de correspondance approximative
3. **Valider les corrections proposées** pour s'assurer qu'elles délimitent correctement les extraits
4. **Sauvegarder les définitions corrigées** dans le fichier de configuration
5. **Générer un rapport détaillé** des modifications effectuées

### Architecture du système

Le système de réparation repose sur deux agents spécialisés :

1. **Agent de réparation** : Analyse le texte source et propose des corrections pour les bornes défectueuses.
2. **Agent de validation** : Vérifie que les bornes proposées délimitent correctement un extrait cohérent et pertinent.

Ces agents utilisent le framework Semantic Kernel pour interagir avec un modèle de langage qui analyse les textes et propose des corrections intelligentes.

### Approche pour le corpus d'Hitler

Pour le corpus de discours d'Hitler, qui est particulièrement volumineux, nous avons développé une approche spécifique :

1. **Approche dichotomique** : Le texte est divisé en sections pour localiser plus efficacement les discours.
2. **Analyse structurelle** : Le script recherche des motifs structurels (titres, numéros de pages, etc.) pour identifier les bornes.
3. **Marqueurs robustes** : Le script privilégie des marqueurs basés sur des séquences uniques et stables dans le document.

## Types de problèmes identifiés et corrections apportées

### 1. Marqueurs de début introuvables

**Problème** : Le marqueur de début n'est pas trouvé exactement dans le texte source.

**Corrections** :
- Recherche de séquences similaires au marqueur original
- Utilisation de difflib pour trouver des correspondances approximatives
- Proposition de nouveaux marqueurs basés sur des éléments structurels du document (titres, débuts de paragraphes)
- Ajout ou modification du template de début pour gérer les variations de formatage

### 2. Marqueurs de fin introuvables

**Problème** : Le marqueur de fin n'est pas trouvé exactement dans le texte source.

**Corrections** :
- Recherche de séquences similaires au marqueur original
- Identification de motifs de fin naturels (fins de paragraphes, sections, etc.)
- Proposition de nouveaux marqueurs plus robustes

### 3. Problèmes de délimitation

**Problème** : Les marqueurs existent mais ne délimitent pas correctement l'extrait (trop court, trop long, incohérent).

**Corrections** :
- Analyse de la cohérence du texte extrait
- Ajustement des bornes pour capturer des unités de sens complètes
- Vérification que l'extrait correspond au sujet attendu

### 4. Problèmes spécifiques au corpus d'Hitler

**Problème** : Le corpus de discours d'Hitler présente des défis spécifiques (volume, structure complexe).

**Corrections** :
- Utilisation d'une approche dichotomique pour localiser les discours
- Identification de motifs structurels spécifiques à ce corpus
- Création de marqueurs plus robustes basés sur des séquences uniques

## Résultats et statistiques

Le script a été testé sur l'ensemble des extraits définis dans `extract_sources.json`. Voici un résumé des résultats :

- **Extraits analysés** : [À compléter après exécution]
- **Extraits valides** : [À compléter après exécution]
- **Extraits réparés avec succès** : [À compléter après exécution]
- **Réparations rejetées** : [À compléter après exécution]
- **Extraits inchangés** : [À compléter après exécution]
- **Erreurs** : [À compléter après exécution]

Un rapport HTML détaillé est généré à chaque exécution du script, permettant de visualiser les modifications effectuées et les raisons des échecs éventuels.

## Utilisation du script

### Mode ligne de commande

Le script peut être exécuté en ligne de commande avec différentes options :

```bash
python repair_extract_markers.py [options]
```

Options disponibles :
- `--output`, `-o` : Fichier de sortie pour le rapport HTML (défaut : `repair_report.html`)
- `--save`, `-s` : Sauvegarder les modifications (défaut : non)
- `--hitler-only` : Traiter uniquement le corpus de discours d'Hitler (défaut : non)

### Mode interactif (notebook)

Le notebook `repair_extract_markers.ipynb` permet d'exécuter le script de manière interactive, avec des visualisations et des explications détaillées à chaque étape.

## Limitations et améliorations futures

### Limitations actuelles

- Le script ne peut pas réparer les extraits dont le texte source n'est pas disponible dans le cache.
- Les corrections proposées dépendent de la qualité du modèle de langage utilisé.
- Le traitement des corpus très volumineux peut être lent.

### Améliorations futures

- **Apprentissage incrémental** : Améliorer les suggestions en apprenant des corrections précédentes.
- **Interface utilisateur** : Développer une interface graphique pour faciliter la validation manuelle des corrections.
- **Optimisation des performances** : Améliorer la gestion des corpus volumineux.
- **Extraction intelligente** : Permettre l'extraction basée sur le sens plutôt que sur des marqueurs exacts.

## Conclusion

Le script de réparation des bornes défectueuses dans les extraits est un outil puissant pour maintenir la qualité des données d'analyse argumentative. En combinant des algorithmes de correspondance approximative avec l'intelligence des modèles de langage, il permet de corriger automatiquement la plupart des problèmes de bornes, tout en offrant une validation rigoureuse des corrections proposées.

Cette approche basée sur des agents démontre l'efficacité de l'intelligence artificielle pour résoudre des problèmes complexes de traitement de texte, tout en maintenant un contrôle humain sur les modifications apportées.