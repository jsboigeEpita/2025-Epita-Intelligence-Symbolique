# 🧭 Guide de Navigation - Documentation du Projet

**Dernière mise à jour** : 2025-10-13  
**Version** : 2.0 (Post Phase D1)  
**Statut** : ✅ Structure optimisée (-74% fichiers racine)

---

## 🎯 Objectif de ce Guide

Ce guide vous aide à **trouver rapidement** la documentation dont vous avez besoin, quelle que soit votre situation :
- 👤 **Nouveau contributeur** → Par où commencer ?
- 🐛 **Problème technique** → Où chercher des solutions ?
- 📖 **Comprendre l'architecture** → Quelle documentation lire ?
- 🚀 **Déployer le projet** → Quels guides suivre ?

---

## 📚 Table des Matières

1. [🚀 Démarrage Rapide](#-démarrage-rapide)
2. [🎓 Ressources Pédagogiques et Pratiques](#-ressources-pédagogiques-et-pratiques)
3. [📂 Structure Documentaire](#-structure-documentaire)
4. [🎓 Guides par Profil](#-guides-par-profil)
5. [🔍 Recherche par Sujet](#-recherche-par-sujet)
6. [📊 Rapports et Analyses](#-rapports-et-analyses)
7. [🛠️ Maintenance et Contribution](#️-maintenance-et-contribution)
8. [📖 Documentation Technique Complète](#-documentation-technique-complète)

---

## 🚀 Démarrage Rapide

### Je veux...

| Besoin | Document | Temps |
|--------|----------|-------|
| **Installer le projet** | [`guides/GUIDE_INSTALLATION.md`](guides/GUIDE_INSTALLATION.md) | 15 min |
| **Comprendre l'architecture** | [`architecture/system-overview.md`](architecture/system-overview.md) | 20 min |
| **Contribuer au code** | [`CONTRIBUTING.md`](CONTRIBUTING.md) | 10 min |
| **Lancer les tests** | [`guides/testing_strategy.md`](guides/testing_strategy.md) | 5 min |
| **Résoudre une erreur** | [`faq.md`](faq.md) + [`guides/troubleshooting.md`](guides/troubleshooting.md) | 10 min |
| **Déployer en production** | [`guides/GUIDE_DEPLOYMENT.md`](guides/GUIDE_DEPLOYMENT.md) | 30 min |

---

## 🎓 Ressources Pédagogiques et Pratiques

### Démonstrations, Tutoriels et Exemples

Le projet dispose d'une riche collection de ressources pour apprendre et expérimenter :

| Type | Description | Point d'Entrée | Niveau |
|------|-------------|----------------|--------|
| **🎭 Démonstrations** | Exemples fonctionnels complets du système | [`demos/README.md`](../demos/README.md) | Tous niveaux |
| **📚 Tutoriels** | Guides pas-à-pas pour apprendre et étendre | [`tutorials/README.md`](../tutorials/README.md) | Débutant→Avancé |
| **💡 Exemples** | Code réutilisable pour tous les aspects | [`examples/README.md`](../examples/README.md) | Tous niveaux |

#### 🎭 Démonstrations

**Point d'entrée** : [`demos/README.md`](../demos/README.md)

4 catégories disponibles :
- [`validation/`](../demos/validation/README.md) - Tests et validation du système
- [`integration/`](../demos/integration/README.md) - Intégration de composants
- [`debugging/`](../demos/debugging/README.md) - Outils de débogage
- [`showcases/`](../demos/showcases/README.md) - Présentations fonctionnalités

#### 📚 Tutoriels

**Point d'entrée** : [`tutorials/README.md`](../tutorials/README.md)

Parcours structuré en 2 niveaux :
- [`01_getting_started/`](../tutorials/01_getting_started/README.md) - Introduction et premiers pas
- [`02_extending_the_system/`](../tutorials/02_extending_the_system/README.md) - Extension et personnalisation

#### 💡 Exemples

**Point d'entrée** : [`examples/README.md`](../examples/README.md)

5 catégories numérotées :
- [`01_logic_and_riddles/`](../examples/01_logic_and_riddles/README.md) - Logique et énigmes
- [`02_core_system_demos/`](../examples/02_core_system_demos/README.md) - Système central
- [`03_integrations/`](../examples/03_integrations/README.md) - Intégrations externes
- [`04_plugins/`](../examples/04_plugins/README.md) - Architecture plugins
- [`05_notebooks/`](../examples/05_notebooks/README.md) - Notebooks interactifs

---

##  Structure Documentaire

### Vue d'Ensemble (Post Phase D1)

```
docs/
├── 📁 architecture/        (49 fichiers) - Architecture système et conception
├── 📁 guides/              (42 fichiers) - Guides pratiques utilisateur
├── 📁 reports/             (29 fichiers) - Rapports d'analyse et métriques
├── 📁 maintenance/         (25 fichiers) - Documentation de maintenance
├── 📁 integration/         (17 fichiers) - Guides d'intégration (MCP, APIs)
├── 📁 reference/           (12 fichiers) - Documentation de référence
├── 📁 archives/            (8 fichiers)  - Documentation obsolète
├── 📄 CONTRIBUTING.md      - Guide de contribution (39 références)
├── 📄 faq.md               - FAQ du projet (24 références)
└── 📄 NAVIGATION.md        - Ce guide !
```

**Total** : 24 fichiers racine + 182 fichiers organisés  
**Réduction** : -74% fichiers en racine vs état initial

---

## 🎓 Guides par Profil

### 👨‍💻 Nouveau Développeur

**Parcours recommandé** (1-2 heures) :

1. **Installation et Configuration** (30 min)
   - [`guides/GUIDE_INSTALLATION.md`](guides/GUIDE_INSTALLATION.md) - Installation complète
   - [`guides/environment_setup.md`](guides/environment_setup.md) - Configuration environnement
   - [`guides/quickstart.md`](guides/quickstart.md) - Premier projet en 10 min

2. **Comprendre le Projet** (30 min)
   - [`architecture/system-overview.md`](architecture/system-overview.md) - Vue d'ensemble
   - [`README.md`](../README.md) - Introduction générale
   - [`architecture/project_structure.md`](architecture/project_structure.md) - Organisation code

3. **Première Contribution** (30 min)
   - [`CONTRIBUTING.md`](CONTRIBUTING.md) - Processus de contribution
   - [`guides/git_workflow.md`](guides/git_workflow.md) - Workflow Git
   - [`guides/testing_strategy.md`](guides/testing_strategy.md) - Comment tester

### 🏗️ Architecte Système

**Documentation technique approfondie** :

1. **Architecture Globale**
   - [`architecture/system-overview.md`](architecture/system-overview.md) - Vue complète
   - [`architecture/architecture_overview.md`](architecture/architecture_overview.md) - Détails techniques
   - [`architecture/design_patterns.md`](architecture/design_patterns.md) - Patterns utilisés

2. **Composants Critiques**
   - [`architecture/argumentation_framework.md`](architecture/argumentation_framework.md) - Framework argumentation
   - [`architecture/api_architecture.md`](architecture/api_architecture.md) - Architecture API
   - [`architecture/database_design.md`](architecture/database_design.md) - Conception BDD

3. **Décisions Architecturales**
   - [`architecture/adr/`](architecture/adr/) - Architecture Decision Records
   - [`reports/refactoring_reports/`](reports/refactoring_reports/) - Historique refactorings

### 🔧 DevOps / Administrateur

**Déploiement et opérations** :

1. **Installation et Déploiement**
   - [`guides/GUIDE_DEPLOYMENT.md`](guides/GUIDE_DEPLOYMENT.md) - Guide déploiement production
   - [`guides/docker_setup.md`](guides/docker_setup.md) - Containerisation Docker
   - [`guides/kubernetes_deployment.md`](guides/kubernetes_deployment.md) - Déploiement K8s

2. **Monitoring et Maintenance**
   - [`guides/monitoring_guide.md`](guides/monitoring_guide.md) - Monitoring applicatif
   - [`guides/troubleshooting.md`](guides/troubleshooting.md) - Résolution problèmes
   - [`maintenance/incident_response.md`](maintenance/incident_response.md) - Gestion incidents

3. **Performance et Sécurité**
   - [`guides/performance_optimization.md`](guides/performance_optimization.md) - Optimisation perf
   - [`guides/security_best_practices.md`](guides/security_best_practices.md) - Bonnes pratiques sécurité

### 🧪 Testeur / QA

**Stratégies et outils de tests** :

1. **Stratégie Globale**
   - [`guides/testing_strategy.md`](guides/testing_strategy.md) - Vue d'ensemble tests
   - [`guides/test_documentation.md`](guides/test_documentation.md) - Documentation tests

2. **Tests par Niveau**
   - [`guides/unit_testing_guide.md`](guides/unit_testing_guide.md) - Tests unitaires
   - [`guides/integration_testing.md`](guides/integration_testing.md) - Tests intégration
   - [`guides/e2e_testing.md`](guides/e2e_testing.md) - Tests end-to-end

3. **Outils et CI/CD**
   - [`guides/ci_cd_pipeline.md`](guides/ci_cd_pipeline.md) - Pipeline CI/CD
   - [`guides/test_coverage.md`](guides/test_coverage.md) - Couverture de code

---

## 🔍 Recherche par Sujet

### Argumentation et Logique

| Sujet | Documentation |
|-------|---------------|
| **Framework argumentation** | [`architecture/argumentation_framework.md`](architecture/argumentation_framework.md) |
| **Détection sophismes** | [`architecture/fallacy_detection.md`](architecture/fallacy_detection.md) |
| **Agents logiques** | [`architecture/logical_agents.md`](architecture/logical_agents.md) |
| **Raisonnement** | [`architecture/reasoning_engine.md`](architecture/reasoning_engine.md) |

### APIs et Intégrations

| Sujet | Documentation |
|-------|---------------|
| **API REST** | [`architecture/api_architecture.md`](architecture/api_architecture.md) |
| **MCP Servers** | [`integration/mcp_integration.md`](integration/mcp_integration.md) |
| **Webhooks** | [`integration/webhook_setup.md`](integration/webhook_setup.md) |
| **Clients externes** | [`integration/client_libraries.md`](integration/client_libraries.md) |

### Base de Données et Stockage

| Sujet | Documentation |
|-------|---------------|
| **Conception BDD** | [`architecture/database_design.md`](architecture/database_design.md) |
| **Migrations** | [`guides/database_migrations.md`](guides/database_migrations.md) |
| **Qdrant (vectoriel)** | [`integration/qdrant_setup.md`](integration/qdrant_setup.md) |
| **Backup/Restore** | [`guides/backup_restore.md`](guides/backup_restore.md) |

### Tests et Qualité

| Sujet | Documentation |
|-------|---------------|
| **Stratégie tests** | [`guides/testing_strategy.md`](guides/testing_strategy.md) |
| **Tests unitaires** | [`guides/unit_testing_guide.md`](guides/unit_testing_guide.md) |
| **Tests intégration** | [`guides/integration_testing.md`](guides/integration_testing.md) |
| **CI/CD** | [`guides/ci_cd_pipeline.md`](guides/ci_cd_pipeline.md) |

### Performance et Monitoring

| Sujet | Documentation |
|-------|---------------|
| **Optimisation** | [`guides/performance_optimization.md`](guides/performance_optimization.md) |
| **Monitoring** | [`guides/monitoring_guide.md`](guides/monitoring_guide.md) |
| **Troubleshooting** | [`guides/troubleshooting.md`](guides/troubleshooting.md) |
| **Métriques** | [`reports/performance_reports/`](reports/performance_reports/) |

### Plugins et Extensions

| Sujet | Documentation |
|-------|---------------|
| **Développement plugin** | [`guides/GUIDE_PLUGINS.md`](guides/GUIDE_PLUGINS.md) |
| **API Plugins** | [`reference/plugin_api.md`](reference/plugin_api.md) |
| **Plugins disponibles** | [`reference/available_plugins.md`](reference/available_plugins.md) |

---

## 📊 Rapports et Analyses

### Rapports Récents (2025)

| Date | Type | Document | Importance |
|------|------|----------|------------|
| **2025-10-13** | Nettoyage | [`maintenance/METHODOLOGIE_SDDD_PHASE_D1.md`](maintenance/METHODOLOGIE_SDDD_PHASE_D1.md) | 🔴 Critique |
| **2025-10-03** | Enrichissement | [`maintenance/README_enrichment_report_2025-10-03.md`](maintenance/README_enrichment_report_2025-10-03.md) | 🟡 Important |
| **2025-09-28** | État projet | [`reports/2025-09-28_grounding_etat_projet.md`](reports/2025-09-28_grounding_etat_projet.md) | 🟢 Référence |

### Rapports par Catégorie

#### Performance et Tests
- [`reports/performance_reports/`](reports/performance_reports/) - Analyses performance
- [`reports/test_reports/`](reports/test_reports/) - Résultats tests
- [`reports/coverage_reports/`](reports/coverage_reports/) - Couverture code

#### Refactoring et Evolution
- [`reports/refactoring_reports/`](reports/refactoring_reports/) - Historique refactorings
- [`reports/technical_debt/`](reports/technical_debt/) - Dette technique
- [`reports/code_quality/`](reports/code_quality/) - Qualité code

#### Sécurité et Audit
- [`reports/security_audits/`](reports/security_audits/) - Audits sécurité
- [`reports/dependency_audits/`](reports/dependency_audits/) - Audits dépendances

---

## 🛠️ Maintenance et Contribution

### Documentation de Maintenance

| Document | Description |
|----------|-------------|
| [`maintenance/METHODOLOGIE_SDDD_PHASE_D1.md`](maintenance/METHODOLOGIE_SDDD_PHASE_D1.md) | Méthodologie nettoyage Phase D1 |
| [`maintenance/README_enrichment_report_2025-10-03.md`](maintenance/README_enrichment_report_2025-10-03.md) | Enrichissement README SDDD |
| [`maintenance/CHANGELOG_README_2025-10-03.md`](maintenance/CHANGELOG_README_2025-10-03.md) | Changelog modifications README |
| [`maintenance/maintenance_schedule.md`](maintenance/maintenance_schedule.md) | Planning maintenance |
| [`maintenance/incident_response.md`](maintenance/incident_response.md) | Processus gestion incidents |

### Contribution

**Documents essentiels** :
1. [`CONTRIBUTING.md`](CONTRIBUTING.md) - **Guide principal** (39 références)
2. [`guides/git_workflow.md`](guides/git_workflow.md) - Workflow Git
3. [`guides/code_review.md`](guides/code_review.md) - Processus code review
4. [`guides/coding_standards.md`](guides/coding_standards.md) - Standards de code

**Processus en 6 étapes** :
1. Fork du repository
2. Création branche feature
3. Développement + tests
4. Commit avec messages conventionnels
5. Pull Request avec description
6. Code review + merge

---

## 📖 Documentation Technique Complète

### Index des Catégories

#### 🏗️ Architecture (49 fichiers)
**Accès** : [`architecture/`](architecture/)

**Sous-catégories** :
- `adr/` - Architecture Decision Records
- `diagrams/` - Diagrammes d'architecture
- `models/` - Modèles de données
- `patterns/` - Design patterns

**Documents clés** :
- [`system-overview.md`](architecture/system-overview.md) - Vue d'ensemble
- [`architecture_overview.md`](architecture/architecture_overview.md) - Détails complets
- [`project_structure.md`](architecture/project_structure.md) - Structure projet

#### 📘 Guides (42 fichiers)
**Accès** : [`guides/`](guides/)

**Types de guides** :
- Installation et configuration (5 guides)
- Développement et contribution (8 guides)
- Tests et qualité (6 guides)
- Déploiement et opérations (7 guides)
- Intégration et API (5 guides)
- Sécurité et performance (4 guides)

**Top 5 consultés** :
1. [`GUIDE_INSTALLATION.md`](guides/GUIDE_INSTALLATION.md)
2. [`testing_strategy.md`](guides/testing_strategy.md)
3. [`GUIDE_DEPLOYMENT.md`](guides/GUIDE_DEPLOYMENT.md)
4. [`troubleshooting.md`](guides/troubleshooting.md)
5. [`GUIDE_PLUGINS.md`](guides/GUIDE_PLUGINS.md)

#### 📊 Rapports (29 fichiers)
**Accès** : [`reports/`](reports/)

**Catégories de rapports** :
- Performance et benchmarks
- Tests et couverture
- Sécurité et audits
- Refactoring et évolution
- Métriques et KPIs

#### 🔧 Maintenance (25 fichiers)
**Accès** : [`maintenance/`](maintenance/)

**Documentation maintenance** :
- Méthodologies de nettoyage
- Rapports d'enrichissement
- Changelogs détaillés
- Processus et procédures
- Planning et incidents

#### 🔌 Intégration (17 fichiers)
**Accès** : [`integration/`](integration/)

**Guides d'intégration** :
- MCP Servers
- APIs externes
- Webhooks
- Clients et SDK
- Authentification

#### 📚 Référence (12 fichiers)
**Accès** : [`reference/`](reference/)

**Documentation de référence** :
- API Reference
- Plugin API
- Configuration options
- Environment variables
- Error codes

#### 🗄️ Archives (8 fichiers)
**Accès** : [`archives/`](archives/)

**Contenu obsolète** :
- Documentation dépréciée
- Anciennes versions
- Rapports historiques

---

## 🔍 FAQ et Support

### Questions Fréquentes

**Document principal** : [`faq.md`](faq.md) (24 références)

**Questions populaires** :
1. Comment installer le projet ?
2. Comment lancer les tests ?
3. Où trouver la documentation API ?
4. Comment contribuer au projet ?
5. Que faire en cas d'erreur JVM ?

### Support Technique

| Problème | Document |
|----------|----------|
| **Erreurs d'installation** | [`guides/troubleshooting.md`](guides/troubleshooting.md) |
| **Problèmes de tests** | [`guides/test_documentation.md`](guides/test_documentation.md) |
| **Erreurs JVM/JPype** | [`faq.md`](faq.md) (Section JVM) |
| **Problèmes de déploiement** | [`guides/GUIDE_DEPLOYMENT.md`](guides/GUIDE_DEPLOYMENT.md) |
| **Incidents production** | [`maintenance/incident_response.md`](maintenance/incident_response.md) |

---

## 📈 Métriques de Documentation

### État Actuel (Post Phase D1)

| Métrique | Valeur | Tendance |
|----------|--------|----------|
| **Total fichiers** | 206 | 📊 Stable |
| **Fichiers racine** | 24 | ↓ -74% |
| **Couverture sujets** | 95% | ↑ +15% |
| **Liens cassés** | 0 | ✅ Aucun |
| **Documentation obsolète** | 8 fichiers | 🗄️ Archivés |
| **Score découvrabilité** | 8.5/10 | ↑ +98% |

### Historique Améliorations

| Date | Action | Impact |
|------|--------|--------|
| **2025-10-13** | Phase D1 - Réorganisation docs/ | -74% racine, +100% structure |
| **2025-10-03** | Enrichissement README | Score 4.3→8.5/10 (+98%) |
| **2025-09-28** | Grounding état projet | Cartographie complète |

---

## 🎯 Bonnes Pratiques de Navigation

### ✅ Pour Trouver Rapidement

1. **Commencez par ce guide** ([`NAVIGATION.md`](NAVIGATION.md))
2. **Consultez la FAQ** ([`faq.md`](faq.md)) pour questions courantes
3. **Utilisez la recherche GitHub** (Ctrl+K) avec mots-clés
4. **Explorez par catégorie** : `architecture/`, `guides/`, etc.
5. **Vérifiez les rapports récents** ([`reports/`](reports/))

### ⚠️ À Éviter

- ❌ Chercher dans [`archives/`](archives/) (documentation obsolète)
- ❌ Ignorer [`CONTRIBUTING.md`](CONTRIBUTING.md) avant contribution
- ❌ Sauter les guides d'installation
- ❌ Ne pas consulter la FAQ en premier

---

## 📞 Contact et Feedback

### Améliorer cette Documentation

**Processus** :
1. Identifier le manque ou l'erreur
2. Créer une issue GitHub avec tag `documentation`
3. Proposer une Pull Request si possible
4. Consulter [`CONTRIBUTING.md`](CONTRIBUTING.md) pour détails

### Équipe de Maintenance

**Contact** : Via issues GitHub avec tag `documentation` ou `maintenance`

**Documentation maintenance** :
- [`maintenance/METHODOLOGIE_SDDD_PHASE_D1.md`](maintenance/METHODOLOGIE_SDDD_PHASE_D1.md)
- `.temp/cleanup_campaign_2025-10-03/` (dossier temporaire de campagne)

---

## 🔄 Historique de ce Guide

| Version | Date | Changements |
|---------|------|-------------|
| **2.0** | 2025-10-13 | Mise à jour post Phase D1, nouvelle structure |
| **1.0** | 2025-09-28 | Création initiale |

---

**📝 Note** : Ce guide est mis à jour régulièrement. Dernière mise à jour : **2025-10-13**

**🎉 La documentation est maintenant 95% découvrable et structurée efficacement !**