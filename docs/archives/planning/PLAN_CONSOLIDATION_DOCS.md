# Plan de Consolidation Documentation (Phase 2)

## 🚨 Problèmes Identifiés
- **79 fichiers** dans docs/ avec structure dispersée
- **Redondances massives** (ex: cleaning_reports avec 14 fichiers lot*)
- **Fichiers géants** (2.4MB+ dans projets/sujets/)
- **Nomenclature incohérente** (français/anglais mélangés)

## 🎯 Actions Prioritaires

### 1. Consolidation Rapports Temporels
- **cleaning_reports/** : 14 fichiers lot* → 1 fichier consolidé
- **rapports/** : 11 fichiers → rationaliser en 3-4 catégories
- **reports/various/** : nettoyer fichiers validation temporaires

### 2. Réorganisation Guides Utilisateur
- **guides/** : 11 fichiers → structure claire par audience
- **projets/sujets/aide/** : consolider avec guides/
- **sherlock_watson/** : 15 fichiers → documentation unifiée

### 3. Architecture et Référence
- **architecture/** : rationaliser 24 fichiers
- **reference/** : maintenir structure mais nettoyer doublons
- **outils/** : consolider avec reference/

### 4. Structure Cible
```
docs/
├── guides/           # Guides utilisateur consolidés
├── architecture/     # Documentation technique
├── reference/        # API et référence
├── projets/         # Projets étudiants (nettoyés)
├── rapports/        # Rapports essentiels uniquement
└── archives/        # Anciens rapports temporels
```

## 📊 Impact Estimé Phase 2
- **Réduction** : 79 → ~35-40 fichiers
- **Économie** : ~30-40% de fichiers docs
- **Navigation** : Structure plus claire
- **Maintenance** : Moins de redondance

## ⚡ Prochaines Actions
1. Nettoyer archives/ et migration_output/
2. Consolidation cleaning_reports/
3. Restructuration guides/
4. Tests fonctionnels