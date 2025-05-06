# Environnement de travail pour l'intégration de la section "Sujets de Projets"

Ce document explique comment utiliser l'environnement de travail mis en place pour l'intégration de la nouvelle section "Sujets de Projets" dans le README.md principal.

## Prérequis

Les outils suivants ont été installés et configurés :

- Git (pour la gestion des branches)
- Python avec pip (pour l'installation de grip)
- Node.js avec npm (pour l'installation de markdownlint-cli)
- grip (pour la prévisualisation Markdown avec le style GitHub)
- markdownlint-cli (pour la validation de la syntaxe Markdown)

## Structure de l'environnement

- `.markdownlint.json` : Configuration de markdownlint pour la validation Markdown
- `compare_markdown.ps1` : Script PowerShell pour comparer le rendu avant/après modification
- `nouvelle_section_sujets_projets.md` : Contenu de la nouvelle section à intégrer

## Utilisation de l'environnement

### 1. Gestion de la branche Git

Une branche dédiée a été créée pour cette tâche :

```powershell
# Vérifier sur quelle branche vous êtes
git branch

# Si vous n'êtes pas sur la branche amelioration-section-projets, basculez dessus
git checkout amelioration-section-projets
```

### 2. Prévisualisation Markdown avec grip

Pour prévisualiser le fichier README.md avec le style GitHub :

```powershell
# Lancer le serveur de prévisualisation
grip README.md

# Accéder à la prévisualisation dans votre navigateur à l'adresse http://localhost:6419/
```

### 3. Validation Markdown avec markdownlint

Pour valider la syntaxe Markdown du README.md :

```powershell
# Valider le fichier README.md
markdownlint README.md

# Valider tous les fichiers Markdown du projet
markdownlint *.md
```

### 4. Utilisation du script de comparaison

Le script `compare_markdown.ps1` permet de comparer le rendu avant/après modification :

```powershell
# Exécuter le script
./compare_markdown.ps1
```

Le script propose un menu interactif avec les options suivantes :
1. Sauvegarder le README.md actuel
2. Générer le rendu HTML du README.md original
3. Générer le rendu HTML du README.md modifié
4. Comparer les rendus HTML (ouvrir dans le navigateur)
5. Valider la syntaxe Markdown avec markdownlint
6. Quitter

### 5. Workflow recommandé

1. Sauvegarder l'état actuel du README.md (option 1 du script)
2. Générer le rendu HTML du README.md original (option 2)
3. Intégrer le contenu de `nouvelle_section_sujets_projets.md` dans le README.md
4. Valider la syntaxe avec markdownlint (option 5)
5. Générer le rendu HTML du README.md modifié (option 3)
6. Comparer les rendus HTML (option 4)
7. Apporter des corrections si nécessaire
8. Une fois satisfait, committer les changements :

```powershell
git add README.md
git commit -m "Ajout de la section Sujets de Projets dans le README.md"
git push origin amelioration-section-projets
```

9. Créer une Pull Request pour fusionner les changements dans la branche principale

## Notes importantes

- La configuration de markdownlint (`.markdownlint.json`) a été adaptée pour ce projet avec les règles suivantes :
  - Longueur de ligne maximale : 120 caractères
  - HTML inline autorisé
  - Pas d'obligation de commencer par un titre
  - Indentation de 4 espaces pour les listes
  - Ponctuation autorisée dans les titres : .,;:!
  - Style de numérotation ordonné
  - Titres dupliqués autorisés dans différents niveaux d'imbrication

- Le script de comparaison crée des fichiers temporaires :
  - `README.md.backup` : Sauvegarde du README.md original
  - `README_original.html` : Rendu HTML du README.md original
  - `README_modified.html` : Rendu HTML du README.md modifié