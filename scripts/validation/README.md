# Scripts de validation

Ce répertoire contient les scripts de validation des fichiers Markdown et des ancres du projet d'analyse argumentative.

## Scripts disponibles

### 1. validate_section_anchors.ps1

Script PowerShell qui vérifie que toutes les ancres dans la section "Sujets de Projets" correspondent à des sections existantes dans le fichier de contenu.

**Fonctionnalités :**
- Extraction des ancres de la table des matières
- Extraction des ancres des sections du contenu
- Vérification que chaque ancre de la table des matières existe dans les sections
- Vérification des sections manquantes dans la table des matières

**Paramètres :**
- `$tocFile` : Fichier de la table des matières (défaut: "section_sujets_projets_toc.md")
- `$contentFile` : Fichier de contenu (défaut: "nouvelle_section_sujets_projets.md")

**Utilisation :**
```powershell
# Exécution avec les paramètres par défaut
./scripts/validation/validate_section_anchors.ps1

# Exécution avec des paramètres personnalisés
./scripts/validation/validate_section_anchors.ps1 -tocFile "mon_toc.md" -contentFile "mon_contenu.md"
```

### 2. validate_toc_anchors.ps1

Script PowerShell qui vérifie que toutes les ancres dans la table des matières correspondent à des sections existantes dans le fichier de contenu.

**Fonctionnalités :**
- Extraction des ancres de la table des matières
- Extraction des ancres des sections du contenu
- Vérification que chaque ancre de la table des matières existe dans les sections

**Paramètres :**
- `$tocFile` : Fichier de la table des matières (défaut: "nouvelle_table_des_matieres.md")
- `$contentFile` : Fichier de contenu (défaut: "nouvelle_section_sujets_projets.md")

**Utilisation :**
```powershell
# Exécution avec les paramètres par défaut
./scripts/validation/validate_toc_anchors.ps1

# Exécution avec des paramètres personnalisés
./scripts/validation/validate_toc_anchors.ps1 -tocFile "mon_toc.md" -contentFile "mon_contenu.md"
```

### 3. compare_markdown.ps1

Script PowerShell pour comparer le rendu avant/après modification du README.md.

**Fonctionnalités :**
- Sauvegarde du README.md actuel
- Génération du rendu HTML du README.md original
- Génération du rendu HTML du README.md modifié
- Comparaison des rendus HTML en les ouvrant dans le navigateur
- Validation de la syntaxe Markdown avec markdownlint

**Prérequis :**
- grip (pour la prévisualisation Markdown avec le style GitHub)
- markdownlint-cli (pour la validation de la syntaxe Markdown)

**Utilisation :**
```powershell
# Exécution du script
./scripts/validation/compare_markdown.ps1
```

Le script propose un menu interactif avec les options suivantes :
1. Sauvegarder le README.md actuel
2. Générer le rendu HTML du README.md original
3. Générer le rendu HTML du README.md modifié
4. Comparer les rendus HTML (ouvrir dans le navigateur)
5. Valider la syntaxe Markdown avec markdownlint
6. Quitter

## Bonnes pratiques

1. **Exécuter les scripts depuis la racine du projet** pour garantir que les chemins relatifs fonctionnent correctement.
2. **Valider les ancres avant de committer** des modifications aux fichiers Markdown pour éviter les liens brisés.
3. **Utiliser le script compare_markdown.ps1** pour vérifier visuellement les modifications apportées au README.md.