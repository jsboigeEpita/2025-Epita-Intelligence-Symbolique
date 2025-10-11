# Guide de Maintenance Oracle Enhanced v2.1.0
*Post-nettoyage des fichiers orphelins - 2025-06-07*

## Vue d'ensemble

Ce guide documente la maintenance du système Oracle Enhanced v2.1.0 après l'organisation complète des fichiers orphelins. Il établit les bonnes pratiques pour maintenir la structure optimisée et prévenir la régression vers un état désorganisé.

## Architecture finale Oracle Enhanced v2.1.0

### Composants principaux
```
🏗️ ARCHITECTURE ORACLE ENHANCED v2.1.0

Core Business Logic:
├── 📁 argumentation_analysis/ - Logique métier principale
│   ├── agents/core/oracle/ - Agents Oracle (Dataset, Moriarty)
│   ├── phases/ - Phases A/B/C/D intégrées
│   └── workflows/ - Workflows Cluedo et extensions

Tests et Validation:
├── 📁 tests/integration/ - Tests d'intégration Oracle/Cluedo
├── 📁 tests/unit/ - Tests unitaires structurés
│   ├── argumentation_analysis/agents/core/oracle/ - Tests Oracle
│   ├── recovered/ - Code précieux récupéré
│   ├── utils/ - Utilitaires de test
│   └── mocks/ - Simulateurs et mocks
├── 📁 tests/validation_sherlock_watson/ - Tests Sherlock Watson
└── 📁 tests/archived/ - Historiques sauvegardés

Documentation et Outils:
├── 📁 docs/ - Documentation complète
├── 📁 logs/ - Rapports et métriques
└── 📁 scripts/ - Scripts de maintenance
```

### Phases Oracle Enhanced intégrées
- **Phase A** : Personnalités distinctes (Sherlock analytique, Watson empathique)
- **Phase B** : Naturalité du dialogue (transitions fluides)
- **Phase C** : Fluidité des transitions (cohérence narrative)
- **Phase D** : Extensions Oracle (dataset + agents Moriarty) ✅

## Procédures de maintenance

### 1. Tests de régression Oracle Enhanced (Hebdomadaire)

#### Script de validation automatique
```bash
# Validation complète Oracle Enhanced
powershell -c "
cd 'D:\2025-Epita-Intelligence-Symbolique'

# Tests d'intégration Oracle
python -m pytest tests/integration/test_oracle_integration.py -v

# Tests workflow Cluedo Extended  
python -m pytest tests/integration/test_cluedo_extended_workflow.py -v

# Tests agents Oracle core
python -m pytest tests/unit/argumentation_analysis/agents/core/oracle/ -v

# Validation finale
if (\$LASTEXITCODE -eq 0) {
    Write-Host '✅ Oracle Enhanced v2.1.0 - Tous les tests passent'
} else {
    Write-Host '❌ Oracle Enhanced v2.1.0 - Échecs détectés'
    exit 1
}
"
```

#### Tests critiques à surveiller
1. **Dataset Access Manager** : `test_dataset_access_manager_fixed.py`
2. **Agent Moriarty Interrogator** : `test_moriarty_interrogator_agent_fixed.py`
3. **Intégration Oracle complète** : `test_oracle_integration.py`
4. **Workflow Cluedo Extended** : `test_cluedo_extended_workflow.py`

### 2. Audit des fichiers orphelins (Mensuel)

#### Script de détection automatique
```python
# scripts/audit_orphelins.py
import os
import json
from datetime import datetime

def audit_orphelins():
    """Détecte les nouveaux fichiers orphelins"""
    
    # Répertoires à surveiller
    watch_dirs = [
        ".",  # Racine du projet
        "tests/",
        "argumentation_analysis/"
    ]
    
    # Patterns de fichiers orphelins
    orphan_patterns = [
        r"test_.*\.py$",  # Tests à la racine
        r".*_temp\.py$",  # Fichiers temporaires
        r".*_backup\.py$",  # Backups oubliés
        r"debug_.*\.py$"  # Scripts de debug
    ]
    
    orphelins_detectes = []
    
    for dir_path in watch_dirs:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if any(re.match(pattern, file) for pattern in orphan_patterns):
                    full_path = os.path.join(root, file)
                    if is_orphelin(full_path):
                        orphelins_detectes.append(full_path)
    
    # Génération du rapport
    rapport = {
        "date_audit": datetime.now().isoformat(),
        "fichiers_orphelins_detectes": len(orphelins_detectes),
        "liste_fichiers": orphelins_detectes,
        "recommandations": generate_recommendations(orphelins_detectes)
    }
    
    with open("logs/audit_orphelins_" + datetime.now().strftime("%Y%m%d") + ".json", "w") as f:
        json.dump(rapport, f, indent=2)
    
    return rapport

def is_orphelin(file_path):
    """Détermine si un fichier est orphelin"""
    # Vérifier s'il est référencé dans le code
    # Vérifier s'il a des imports/exports
    # Vérifier la date de dernière modification
    pass

def generate_recommendations(orphelins):
    """Génère des recommandations pour chaque fichier orphelin"""
    pass

if __name__ == "__main__":
    audit_orphelins()
```

### 3. Maintenance de la documentation (À chaque fonctionnalité)

#### Checklist de synchronisation
- [ ] **README.md** mis à jour avec nouvelles fonctionnalités
- [ ] **Documentation technique** des nouveaux agents Oracle
- [ ] **Tests unitaires** documentés avec exemples
- [ ] **Architecture** mise à jour si modifications structurelles
- [ ] **Guide d'installation** actualisé si nouvelles dépendances

#### Template pour nouvelles fonctionnalités Oracle
```markdown
## Nouvelle Fonctionnalité Oracle : [NOM]

### Description
[Description de la fonctionnalité]

### Agents impliqués
- **Dataset Access Manager** : [Impact]
- **Moriarty Interrogator** : [Impact] 
- **[Autres agents]** : [Impact]

### Tests associés
- `tests/unit/...` : [Description des tests unitaires]
- `tests/integration/...` : [Description des tests d'intégration]

### Configuration requise
```python
# Configuration exemple
CONFIG = {
    "oracle_enhanced": {
        "version": "v2.1.0",
        "nouvelle_feature": {
            # Paramètres
        }
    }
}
```

### Impact sur l'architecture
[Description des modifications architecturelles]
```

### 4. Sauvegarde systématique (Avant refactoring majeur)

#### Script de sauvegarde automatique
```bash
# scripts/backup_before_refactoring.ps1
param(
    [string]$Description = "Refactoring",
    [string]$BackupDir = "archives"
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "backup_${Description}_${timestamp}.tar.gz"
$backupPath = "${BackupDir}/${backupName}"

Write-Host "🔄 Création de la sauvegarde avant refactoring..."

# Création de l'archive
tar -czf $backupPath --exclude="*.git*" --exclude="__pycache__" --exclude="*.pyc" .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Sauvegarde créée : $backupPath"
    
    # Métadonnées de la sauvegarde
    $metadata = @{
        "date_creation" = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        "description" = $Description
        "version_oracle" = "v2.1.0"
        "fichier_backup" = $backupName
        "taille_Mo" = [math]::Round((Get-Item $backupPath).Length / 1MB, 2)
    } | ConvertTo-Json -Depth 2
    
    $metadata | Out-File "${BackupDir}/metadata_${timestamp}.json"
    
    Write-Host "📋 Métadonnées sauvegardées"
} else {
    Write-Host "❌ Échec de la sauvegarde"
    exit 1
}
```

### 5. Nettoyage sécurisé automatique

#### Script de nettoyage intelligent
```python
# scripts/cleanup_safe.py
import os
import shutil
import json
from datetime import datetime, timedelta

class SafeCleanup:
    def __init__(self):
        self.protected_files = self.load_protected_files()
        self.backup_created = False
    
    def load_protected_files(self):
        """Charge la liste des fichiers protégés"""
        try:
            with open("config/protected_files.json", "r") as f:
                return json.load(f)
        except:
            return {
                "critical_files": [
                    "argumentation_analysis/agents/core/oracle/*.py",
                    "tests/integration/test_oracle_*.py",
                    "tests/unit/argumentation_analysis/agents/core/oracle/*.py"
                ],
                "precious_files": [
                    "tests/unit/recovered/*.py",
                    "tests/utils/*.py",
                    "docs/*.md"
                ]
            }
    
    def create_backup(self):
        """Crée une sauvegarde avant nettoyage"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"archives/pre_cleanup_backup_{timestamp}.tar.gz"
        
        os.system(f"tar -czf {backup_path} --exclude='*.git*' .")
        self.backup_created = True
        return backup_path
    
    def identify_safe_to_clean(self):
        """Identifie les fichiers sûrs à nettoyer"""
        safe_patterns = [
            r".*_temp\.py$",
            r".*_backup\.py$", 
            r"debug_.*\.py$",
            r"test_.*_old\.py$"
        ]
        
        candidates = []
        for root, dirs, files in os.walk("."):
            for file in files:
                full_path = os.path.join(root, file)
                if self.is_safe_to_clean(full_path, safe_patterns):
                    candidates.append(full_path)
        
        return candidates
    
    def is_safe_to_clean(self, file_path, patterns):
        """Vérifie si un fichier est sûr à nettoyer"""
        # Vérifier qu'il n'est pas protégé
        if self.is_protected(file_path):
            return False
        
        # Vérifier les patterns de nettoyage sûr
        import re
        for pattern in patterns:
            if re.match(pattern, os.path.basename(file_path)):
                return True
        
        return False
    
    def is_protected(self, file_path):
        """Vérifie si un fichier est protégé"""
        import fnmatch
        
        for pattern in self.protected_files.get("critical_files", []):
            if fnmatch.fnmatch(file_path, pattern):
                return True
        
        for pattern in self.protected_files.get("precious_files", []):
            if fnmatch.fnmatch(file_path, pattern):
                return True
        
        return False
    
    def cleanup(self, dry_run=True):
        """Exécute le nettoyage sécurisé"""
        if not self.backup_created:
            backup_path = self.create_backup()
            print(f"✅ Sauvegarde créée : {backup_path}")
        
        candidates = self.identify_safe_to_clean()
        
        if dry_run:
            print("🔍 Mode simulation - Fichiers qui seraient nettoyés :")
            for file in candidates:
                print(f"  - {file}")
        else:
            print("🗑️ Nettoyage en cours...")
            for file in candidates:
                try:
                    os.remove(file)
                    print(f"  ✅ Supprimé : {file}")
                except Exception as e:
                    print(f"  ❌ Erreur : {file} - {e}")
        
        return candidates

if __name__ == "__main__":
    cleanup = SafeCleanup()
    cleanup.cleanup(dry_run=True)  # Mode simulation par défaut
```

## Surveillance et alertes

### Métriques à surveiller
1. **Nombre de fichiers orphelins** : ≤ 30 (seuil d'alerte)
2. **Couverture des tests Oracle** : ≥ 90%
3. **Performance des tests d'intégration** : ≤ 5 minutes
4. **Taille du projet** : Croissance contrôlée (≤ 20%/mois)

### Alertes automatiques
```bash
# Cron job pour surveillance quotidienne
# 0 9 * * * /path/to/surveillance_oracle.sh

#!/bin/bash
# surveillance_oracle.sh

cd "D:\2025-Epita-Intelligence-Symbolique"

# Compter les fichiers orphelins
orphelins=$(find . -name "test_*.py" -not -path "./tests/*" | wc -l)

if [ $orphelins -gt 30 ]; then
    echo "⚠️ ALERTE : $orphelins fichiers orphelins détectés (seuil: 30)"
    # Envoyer notification (email, Slack, etc.)
fi

# Vérifier les tests Oracle
python -m pytest tests/integration/test_oracle_integration.py --quiet
if [ $? -ne 0 ]; then
    echo "❌ ALERTE : Tests Oracle Enhanced en échec"
    # Envoyer notification critique
fi
```

## Bonnes pratiques de développement

### Règles pour nouveaux fichiers
1. **Pas de fichiers à la racine** sauf configuration
2. **Tests unitaires** dans `tests/unit/[module]/`
3. **Tests d'intégration** dans `tests/integration/`
4. **Documentation** systématique pour nouveaux agents Oracle
5. **Sauvegarde** avant modifications majeures

### Convention de nommage
```
✅ CORRECT :
├── tests/unit/argumentation_analysis/agents/core/oracle/test_new_agent.py
├── tests/integration/test_oracle_new_feature.py
├── docs/ORACLE_NEW_FEATURE.md

❌ INCORRECT :
├── test_new_feature.py (à la racine)
├── new_test.py (nom non descriptif)
├── temp_test.py (fichier temporaire)
```

### Checklist avant commit
- [ ] Tests passent (`pytest tests/integration/`)
- [ ] Pas de fichiers orphelins créés
- [ ] Documentation mise à jour
- [ ] Code review effectuée
- [ ] Sauvegarde créée si refactoring majeur

## Restauration en cas de problème

### Procédure de rollback
```bash
# En cas de problème après nettoyage
cd "D:\2025-Epita-Intelligence-Symbolique"

# Restaurer depuis la dernière sauvegarde
tar -xzf archives/pre_cleanup_backup_[TIMESTAMP].tar.gz

# Vérifier l'intégrité
python -m pytest tests/integration/ -v

# Valider la restauration
echo "✅ Système restauré à l'état précédent"
```

### Points de contrôle recommandés
1. **Avant nettoyage** : Sauvegarde complète
2. **Après modifications Oracle** : Tests d'intégration
3. **Chaque semaine** : Validation globale
4. **Chaque mois** : Audit complet + métriques

---

**📘 Guide maintenu par l'équipe Oracle Enhanced - Dernière mise à jour : 2025-06-07**

*Ce guide assure la pérennité de l'organisation optimisée après le nettoyage des fichiers orphelins.*