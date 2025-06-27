# Analyseur de Documentation Obsolète Oracle Enhanced v2.1.0

## Vue d'ensemble

L'analyseur de documentation obsolète est un outil essentiel de maintenance qui détecte automatiquement les liens internes brisés dans la documentation du projet Oracle Enhanced v2.1.0.

## Fonctionnalités

### ✅ Détection Automatique
- **Liens Markdown** : `[texte](chemin/vers/fichier.ext)`
- **Liens HTML** : `<a href="chemin">`
- **Références de code** : `` `fichier.py` ``
- **Liens relatifs** : `./`, `../`, `/`

### ✅ Formats Supportés
- **Markdown** (`.md`)
- **reStructuredText** (`.rst`) 
- **Texte brut** (`.txt`)
- **HTML** (`.html`)

### ✅ Rapports Détaillés
- Rapport Markdown structuré
- Export JSON pour intégration
- Statistiques de santé documentaire
- Recommandations de correction

## Installation et Configuration

### Prérequis
```bash
# Python 3.8+
python --version

# Dépendances du projet Oracle Enhanced
pip install -r requirements.txt
```

### Vérification de l'installation
```bash
# Test rapide
python scripts/maintenance/analyze_obsolete_documentation.py --help
```

## Utilisation

### Mode Analyse Rapide (Markdown uniquement)
```bash
# Via script d'activation d'environnement
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python scripts/maintenance/analyze_obsolete_documentation.py --quick-scan"

# Direct
python scripts/maintenance/analyze_obsolete_documentation.py --quick-scan
```

### Mode Analyse Complète (tous formats)
```bash
# Analyse complète avec rapport Markdown
python scripts/maintenance/analyze_obsolete_documentation.py --full-analysis

# Analyse avec rapport JSON
python scripts/maintenance/analyze_obsolete_documentation.py --full-analysis --output-format json

# Analyse avec fichier de sortie personnalisé
python scripts/maintenance/analyze_obsolete_documentation.py --full-analysis --output logs/custom_report.md
```

### Maintenance Coordonnée
```bash
# Maintenance complète via orchestrateur
python scripts/maintenance/run_documentation_maintenance.py

# Maintenance rapide
python scripts/maintenance/run_documentation_maintenance.py --quick-scan

# Analyse obsolète uniquement
python scripts/maintenance/run_documentation_maintenance.py --obsolete-only
```

## Options de Configuration

### Arguments Principaux
| Argument | Description | Défaut |
|----------|-------------|---------|
| `--project-root` | Racine du projet | `.` |
| `--output` | Fichier de sortie | Auto-généré |
| `--output-format` | Format (`markdown`/`json`) | `markdown` |
| `--quick-scan` | Analyse rapide (.md uniquement) | `false` |
| `--full-analysis` | Analyse complète (tous formats) | `false` |

### Exemples d'Usage Avancé
```bash
# Analyse d'un sous-projet spécifique
python scripts/maintenance/analyze_obsolete_documentation.py \
  --project-root ./argumentation_analysis \
  --output logs/subproject_analysis.md

# Analyse JSON pour intégration CI/CD
python scripts/maintenance/analyze_obsolete_documentation.py \
  --full-analysis \
  --output-format json \
  --output reports/doc_health.json
```

## Interprétation des Résultats

### Rapport Markdown

Le rapport généré contient :

#### 📊 Résumé Exécutif
- Nombre de fichiers analysés
- Total des liens internes
- Liens brisés détectés
- Pourcentage de santé documentaire

#### 🚨 Liens Brisés Détaillés
Pour chaque lien brisé :
- Chemin du lien brisé
- Fichier source et numéro de ligne
- Chemin cible résolu
- Description du problème

#### 📋 Analyse par Fichier
- Statut de chaque fichier de documentation
- Liens trouvés vs liens brisés
- Liste détaillée des erreurs

#### 🔧 Recommandations
- Actions prioritaires
- Commandes de maintenance
- Bonnes pratiques

### Codes de Sortie
- **0** : Documentation saine, aucun lien brisé
- **1** : Documentation obsolète détectée

### Exemples de Sortie
```bash
[RESUME]:
   Fichiers analyses: 544
   Liens totaux: 11969
   Liens brises: 11146
   Pourcentage de liens valides: 6.9%

[ATTENTION] Documentation obsolete detectee!
   Consulter le rapport: logs/obsolete_documentation_report_20250607_192958.md
```

## Intégration aux Workflows

### Validation Pré-Commit
```bash
# Ajouter au script de validation
python scripts/maintenance/analyze_obsolete_documentation.py --quick-scan
if [ $? -ne 0 ]; then
    echo "⚠️ Documentation obsolète détectée - voir rapport"
    exit 1
fi
```

### CI/CD Pipeline
```yaml
# Exemple GitHub Actions
- name: Check Documentation Health
  run: |
    python scripts/maintenance/analyze_obsolete_documentation.py \
      --full-analysis \
      --output-format json
    
- name: Upload Documentation Report
  uses: actions/upload-artifact@v3
  with:
    name: documentation-health-report
    path: logs/obsolete_documentation_report_*.json
```

### Maintenance Programmée
```bash
# Crontab pour maintenance hebdomadaire
0 2 * * 1 cd /path/to/project && python scripts/maintenance/run_documentation_maintenance.py --full-analysis
```

## Dépannage

### Problèmes Courants

#### Erreur d'encodage
```bash
# Solution : Forcer l'encodage UTF-8
set PYTHONIOENCODING=utf-8
python scripts/maintenance/analyze_obsolete_documentation.py --quick-scan
```

#### Erreur de permissions
```bash
# Vérifier les permissions du dossier logs
mkdir -p logs
chmod 755 logs
```

#### Performance sur gros projets
```bash
# Utiliser l'analyse rapide pour les gros volumes
python scripts/maintenance/analyze_obsolete_documentation.py --quick-scan

# Ou analyser par sous-dossiers
for dir in docs tests examples; do
    python scripts/maintenance/analyze_obsolete_documentation.py \
      --project-root ./$dir \
      --output logs/analysis_$dir.md
done
```

## Bonnes Pratiques

### 📅 Fréquence Recommandée
- **Développement actif** : Analyse rapide quotidienne
- **Maintenance régulière** : Analyse complète hebdomadaire
- **Avant releases** : Analyse complète obligatoire

### 🎯 Optimisation des Performances
- Utiliser `--quick-scan` pour les vérifications fréquentes
- Analyser par sections pour les très gros projets
- Exporter en JSON pour l'intégration automatisée

### 🔧 Correction des Liens Brisés
1. **Prioriser les fichiers principaux** (README, guides utilisateur)
2. **Mettre à jour les liens relatifs** après reorganizations
3. **Supprimer les références** à des fichiers définitivement supprimés
4. **Documenter les changements** dans les logs de modification

## Extensions et Personnalisation

### Ajouter de Nouveaux Formats
```python
# Dans DocumentationLinkAnalyzer.__init__()
self.doc_extensions = {'.md', '.rst', '.txt', '.html', '.adoc'}
```

### Personnaliser les Patterns de Liens
```python
# Ajouter des patterns spécifiques
self.link_patterns.append(r'<!-- LINK: ([^>]+) -->')
```

### Filtres d'Exclusion
```python
# Exclure certains répertoires
excluded_dirs = {'.git', 'node_modules', '__pycache__'}
```

## Support et Contribution

### Signaler un Bug
1. Vérifier les issues existantes
2. Fournir les logs complets
3. Inclure l'environnement de test

### Contribuer des Améliorations
1. Fork du repository
2. Tests de régression
3. Documentation mise à jour
4. Pull request avec description

---

*Analyseur de Documentation Obsolète Oracle Enhanced v2.1.0*  
*Dernière mise à jour : 2025-06-07*