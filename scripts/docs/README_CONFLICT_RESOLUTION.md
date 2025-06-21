# 🔥 GUIDE DE RÉSOLUTION DES CONFLITS GIT

## 📋 Vue d'ensemble

Ce répertoire contient des outils avancés pour diagnostiquer et résoudre les conflits Git avec le dépôt distant, en particulier pour gérer la corruption de l'historique Git et générer des marqueurs de conflit détaillés.

## 🛠️ Scripts disponibles

### 1. `diagnostic_git_corruption.ps1`
Script principal de diagnostic et correction de corruption Git avec synchronisation du dépôt distant.

### 2. `git_conflict_resolver.ps1` 
Script spécialisé dans la résolution des conflits avec génération de marqueurs améliorés.

## 🚀 Utilisation rapide

### Diagnostic complet et synchronisation
```powershell
# Diagnostic standard
.\scripts\diagnostic_git_corruption.ps1

# Mode forcé sans confirmation
.\scripts\diagnostic_git_corruption.ps1 -Force

# Spécifier remote et branche
.\scripts\diagnostic_git_corruption.ps1 -Remote origin -Branch main -Force
```

### Résolution des conflits

```powershell
# Génération de marqueurs de conflit détaillés (recommandé)
.\scripts\git_conflict_resolver.ps1 -Mode markers

# Résolution automatique (garde version locale)
.\scripts\git_conflict_resolver.ps1 -Mode auto

# Résolution manuelle guidée
.\scripts\git_conflict_resolver.ps1 -Mode manual

# Rapport d'état des conflits
.\scripts\git_conflict_resolver.ps1 -Mode report
```

## 📖 Scénarios d'utilisation

### Scénario 1 : Corruption de l'historique Git détectée

```powershell
# 1. Diagnostic initial
.\scripts\diagnostic_git_corruption.ps1

# 2. Si des conflits sont détectés, générer les marqueurs
.\scripts\git_conflict_resolver.ps1 -Mode markers

# 3. Résoudre manuellement les conflits dans les fichiers

# 4. Vérifier la résolution
.\scripts\git_conflict_resolver.ps1 -Mode report

# 5. Finaliser
git add .
git commit -m "Résolution conflits après corruption"
git push origin main
```

### Scénario 2 : Synchronisation forcée avec dépôt distant

```powershell
# Synchronisation complète avec gestion automatique des conflits
.\scripts\diagnostic_git_corruption.ps1 -Force -ResolveConflicts markers
```

### Scénario 3 : Conflits lors d'un merge en cours

```powershell
# Si un merge est en cours et produit des conflits
git status  # Vérifier l'état

# Générer des marqueurs améliorés pour faciliter la résolution
.\scripts\git_conflict_resolver.ps1 -Mode markers

# Après résolution manuelle
.\scripts\git_conflict_resolver.ps1 -Mode report
git commit  # Finaliser le merge
```

## 🎯 Fonctionnalités avancées

### Marqueurs de conflit améliorés

Le script `git_conflict_resolver.ps1` en mode `markers` génère des marqueurs de conflit enrichis :

```
<<<<<<< HEAD (VERSION LOCALE - Conflit #1)
# CONFLIT #1 DÉTECTÉ dans fichier.py
# Ligne 45-52
# Choisir UNE des options ci-dessous:

# OPTION 1: VERSION LOCALE (vos modifications)
def ma_fonction():
    return "version locale"

# ==================================================
# SÉPARATEUR - NE PAS MODIFIER CETTE LIGNE
# ==================================================

# OPTION 2: VERSION DISTANTE (modifications du dépôt)
def ma_fonction():
    return "version distante"

# OPTION 3: FUSION MANUELLE
# Combinez les deux versions ci-dessus selon vos besoins
# Puis supprimez TOUS les commentaires et marqueurs
>>>>>>> origin/main (VERSION DISTANTE - 20:04:51)
```

### Sauvegardes automatiques

- **Diagnostic :** Sauvegarde automatique avant toute modification
- **Conflits :** Fichiers `.conflict_backup_TIMESTAMP` créés automatiquement
- **Nettoyage :** Suppression automatique après résolution réussie

### Rapports détaillés

Génération automatique de rapports Markdown avec :
- Liste complète des conflits
- Instructions de résolution étape par étape
- Commandes Git recommandées
- Historique des sauvegardes

## ⚠️ Situations d'urgence

### Corruption totale du dépôt Git

```powershell
# Si .git n'existe pas ou est corrompu
.\scripts\diagnostic_git_corruption.ps1 -Force

# Le script proposera :
# 1. Initialisation d'un nouveau dépôt
# 2. Configuration du remote
# 3. Récupération depuis le distant
# 4. Résolution des conflits
```

### Échec de synchronisation

```powershell
# En cas d'échec de push
git status
git log --oneline -5

# Diagnostic approfondi
.\scripts\diagnostic_git_corruption.ps1

# Si nécessaire, push forcé (ATTENTION)
git push origin main --force-with-lease
```

### Recovery depuis les sauvegardes

```powershell
# Lister les sauvegardes disponibles
Get-ChildItem -Recurse -Filter "*.backup_*" | Sort-Object LastWriteTime

# Restaurer un fichier spécifique
Copy-Item "fichier.py.backup_20250106_200451" "fichier.py" -Force

# Vérifier l'état après restauration
git status
git diff
```

## 🔧 Configuration recommandée

### Avant utilisation

```powershell
# Vérifier la configuration Git
git config --list --local

# Configurer si nécessaire
git config user.name "Votre Nom"
git config user.email "votre.email@example.com"

# Vérifier les remotes
git remote -v
```

### Variables d'environnement utiles

```powershell
# Pour éviter les problèmes d'encodage
$env:LANG = "en_US.UTF-8"

# Pour les outils de merge graphiques
git config merge.tool vscode
git config mergetool.vscode.cmd 'code --wait $MERGED'
```

## 📚 Référence des commandes

### Commandes Git essentielles post-conflit

```bash
# Vérifier l'état
git status
git diff --name-only

# Gérer les conflits
git mergetool                    # Outil graphique
git checkout --ours fichier     # Garder version locale
git checkout --theirs fichier   # Garder version distante

# Finaliser
git add .
git commit -m "Résolution conflits"
git push origin main

# Annuler si nécessaire
git merge --abort               # Annuler merge en cours
git reset --hard HEAD~1        # Annuler dernier commit (DANGER)
```

### Vérifications post-résolution

```bash
# Vérifier qu'aucun marqueur ne reste
grep -r "<<<<<<< \|======= \|>>>>>>> " .

# Vérifier l'intégrité
git fsck --full

# Voir l'historique
git log --oneline --graph -10

# Comparer avec le distant
git diff HEAD origin/main
```

## 🆘 Support et troubleshooting

### Problèmes courants

1. **"Permission denied" lors du push**
   ```bash
   git remote set-url origin https://username:token@github.com/user/repo.git
   ```

2. **Merge conflict non résolu**
   ```powershell
   .\scripts\git_conflict_resolver.ps1 -Mode markers
   # Puis éditer manuellement les fichiers
   ```

3. **Historique divergent**
   ```bash
   git pull origin main --rebase
   # Ou si nécessaire :
   git pull origin main --allow-unrelated-histories
   ```

### Logs de débogage

Les scripts génèrent automatiquement :
- Rapports de conflit dans `scripts/conflict_report_*.md`
- Fichiers de sauvegarde avec timestamp
- Messages détaillés en console

### Contact

Ce système a été conçu pour être autonome. En cas de problème critique :
1. Consultez les sauvegardes automatiques
2. Utilisez `git reflog` pour voir l'historique des actions
3. Relancez les scripts en mode diagnostic

---

*Documentation générée pour le système de résolution des conflits Git - 2025*
