# Guide de Contribution à la Documentation

Ce document décrit les règles et bonnes pratiques à suivre pour contribuer à la documentation du projet d'Intelligence Symbolique.

## Principes Généraux

1. **Clarté et concision** : Privilégiez un style d'écriture clair et concis.
2. **Cohérence** : Maintenez une cohérence dans la terminologie et le style à travers tous les documents.
3. **Structure** : Respectez la structure hiérarchique de la documentation.
4. **Mise à jour** : Assurez-vous que les informations sont à jour et pertinentes.
5. **Liens croisés** : Utilisez des liens relatifs pour référencer d'autres documents.

## Structure de la Documentation

La documentation est organisée selon une structure hiérarchique à trois niveaux maximum :
- **Niveau 1** : Catégories principales (architecture, composants, guides, etc.)
- **Niveau 2** : Sous-catégories ou thèmes spécifiques
- **Niveau 3** : Documents individuels

Pour plus de détails sur la structure, consultez le fichier [docs/STRUCTURE.md](docs/STRUCTURE.md).

## Conventions de Nommage

1. **Fichiers** : Utilisez le format `snake_case` pour tous les noms de fichiers (ex: `guide_utilisation.md`).
2. **Répertoires** : Utilisez des noms en minuscules sans espaces ni caractères spéciaux.
3. **README.md** : Chaque répertoire doit contenir un fichier README.md servant de point d'entrée.

## Format des Documents

### En-tête

Chaque document doit commencer par un titre de niveau 1 suivi d'une brève description :

```markdown
# Titre du Document

Brève description du contenu et de l'objectif du document.
```

### Structure des Sections

Utilisez une hiérarchie cohérente de titres :
- `#` pour le titre principal
- `##` pour les sections principales
- `###` pour les sous-sections
- `####` pour les sous-sous-sections (à éviter si possible)

### Listes et Tableaux

- Utilisez des listes à puces (`-`) pour les énumérations sans ordre particulier.
- Utilisez des listes numérotées (`1.`) pour les séquences ou étapes.
- Structurez les informations complexes dans des tableaux pour une meilleure lisibilité.

### Code et Exemples

Encadrez les blocs de code avec des triples backticks et spécifiez le langage :

```markdown
```python
def exemple():
    return "Ceci est un exemple de code Python"
```
```

Pour le code inline, utilisez des backticks simples : `variable = valeur`.

## Processus de Contribution

1. **Vérification** : Avant de créer un nouveau document, vérifiez qu'il n'existe pas déjà.
2. **Placement** : Placez le document dans le répertoire approprié selon la structure.
3. **Liens** : Mettez à jour les fichiers README.md pertinents pour inclure des liens vers votre nouveau document.
4. **Revue** : Soumettez votre contribution pour revue par l'équipe.

## Maintenance de la Documentation

### Révisions Régulières

La documentation doit être révisée régulièrement pour :
- Corriger les erreurs ou imprécisions
- Mettre à jour les informations obsolètes
- Améliorer la clarté et la structure

### Gestion des Versions

- Documentez les changements majeurs dans le fichier CHANGELOG.md
- Archivez les versions obsolètes plutôt que de les supprimer

## Ressources Utiles

- [Guide de syntaxe Markdown](https://www.markdownguide.org/basic-syntax/)
- [Mermaid pour les diagrammes](https://mermaid-js.github.io/mermaid/#/)
- [Documentation sur les conventions du projet](./guides/conventions_importation.md)