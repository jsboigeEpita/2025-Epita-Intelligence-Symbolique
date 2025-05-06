# Documentation supplémentaire

Ce répertoire contient la documentation supplémentaire du projet d'analyse argumentative. Ces documents vous aideront à comprendre le projet en profondeur et à contribuer efficacement.

## Documents disponibles

### 1. README_cleanup_obsolete_files.md

Documentation détaillée pour le script `cleanup_obsolete_files.py` qui permet de gérer la suppression sécurisée des fichiers obsolètes du projet.

**Contenu :**
- Contexte et objectifs du script
- Liste des fichiers concernés
- Instructions d'utilisation avec exemples
- Description des options disponibles
- Structure des archives générées
- Mécanismes de sécurité implémentés
- Bonnes pratiques recommandées

### 2. Sujets de Projets

Les sujets de projets sont maintenant intégrés directement dans la section "Sujets de Projets" du README.md principal.

**Contenu :**
- Introduction aux sujets de projets
- Organisation des projets en catégories
- Structure standardisée de présentation des sujets
- Liste des sujets proposés par catégorie

## Guide de contribution pour les étudiants

### Utilisation de la documentation

#### Pour les nouveaux contributeurs

1. Commencez par lire le [README.md](../README.md) principal à la racine du projet
2. Référez-vous aux documents spécifiques selon vos besoins :
   - Pour le nettoyage du projet : [README_cleanup_obsolete_files.md](README_cleanup_obsolete_files.md)
3. Explorez les sujets de projets dans la section [Sujets de Projets](../README.md#sujets-de-projets) du README principal

#### Pour les mainteneurs

1. Assurez-vous que la documentation est à jour avec le code
2. Utilisez les scripts de validation pour vérifier l'intégrité des liens et des ancres
3. Suivez les bonnes pratiques documentées pour maintenir la cohérence du projet

### Ajout de nouvelle documentation

Si vous souhaitez contribuer à la documentation du projet, voici quelques conseils :

1. **Choisissez un format cohérent** :
   - Utilisez le format Markdown (.md) pour tous les documents
   - Suivez la structure des documents existants
   - Incluez une table des matières pour les documents longs

2. **Nommage des fichiers** :
   - Pour les README spécifiques : `README_[sujet].md`
   - Pour les rapports : `rapport_[sujet].md`
   - Pour les guides : `guide_[sujet].md`

3. **Structure recommandée** :
   - Introduction claire expliquant l'objectif du document
   - Sections bien délimitées avec des titres explicites
   - Exemples concrets et code si nécessaire
   - Conclusion ou résumé des points importants

4. **Mise à jour du README principal** :
   - Ajoutez une entrée pour votre nouveau document dans ce README.md
   - Incluez une brève description du contenu

### Workflow de contribution à la documentation

1. **Créez une branche** dans votre fork pour votre documentation :
   ```bash
   git checkout -b doc/votre-sujet
   ```

2. **Créez ou modifiez** les fichiers de documentation :
   ```bash
   # Créez votre fichier de documentation
   touch docs/guide_votre_sujet.md
   
   # Éditez le fichier avec votre contenu
   nano docs/guide_votre_sujet.md
   ```

3. **Mettez à jour ce README.md** pour référencer votre document :
   ```bash
   nano docs/README.md
   ```

4. **Vérifiez la qualité** de votre documentation :
   - Utilisez un outil comme markdownlint pour valider la syntaxe
   - Vérifiez les liens et références
   - Assurez-vous que le document est clair et bien structuré

5. **Committez et poussez vos changements** :
   ```bash
   git add docs/guide_votre_sujet.md docs/README.md
   git commit -m "Ajout d'un guide sur [votre sujet]"
   git push origin doc/votre-sujet
   ```

6. **Créez une Pull Request** vers le dépôt principal

## Suggestions de documentation à créer

Si vous cherchez des idées pour contribuer à la documentation, voici quelques suggestions :

1. **Guides d'utilisation** :
   - Guide détaillé d'utilisation de l'interface utilisateur
   - Guide d'interprétation des résultats d'analyse
   - Guide de dépannage des problèmes courants

2. **Documentation technique** :
   - Architecture détaillée du système multi-agents
   - Flux de données entre les composants
   - Protocoles de communication entre agents

3. **Tutoriels** :
   - Tutoriel pas à pas pour créer un nouvel agent
   - Tutoriel d'extension de la taxonomie des sophismes
   - Tutoriel d'intégration avec des outils externes

4. **Documentation de référence** :
   - Référence complète des API internes
   - Glossaire des termes techniques utilisés
   - Index des fonctionnalités principales

## Ressources pour la rédaction de documentation

- [Guide de syntaxe Markdown](https://www.markdownguide.org/basic-syntax/)
- [Bonnes pratiques de documentation technique](https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/)
- [Outils de validation Markdown](https://github.com/DavidAnson/markdownlint)
- [Modèles de documentation](https://github.com/kylelobo/The-Documentation-Compendium)