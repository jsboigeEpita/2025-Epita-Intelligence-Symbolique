# Stratégie d'Organisation Phase D3 - tests/

**Date** : 2025-10-14  
**Basé sur** : CARTOGRAPHIE_TESTS.md, BASELINE_PYTEST.md, RAPPORT_GROUNDING_D3.md

---

## 🎯 Principe Directeur

**Progression Prudente : Zones Faible Risque → Risque Élevé**

**Contraintes ABSOLUES** :
- ✅ `pytest -v` après **CHAQUE** manipulation (non négociable)
- ✅ Maximum **15 fichiers** par commit
- ✅ Documentation en temps réel
- ✅ Si pytest échoue : **ROLLBACK immédiat**
- ✅ Demander validation utilisateur en cas de doute

**Méthodologie** :
1. **Grounding sémantique** avant chaque phase
2. **Lots atomiques** (10-15 fichiers max)
3. **Validation pytest** après chaque lot
4. **Documentation continue** des actions et résultats

---

## 🚀 Phase D3.0 : Préparation (ACTUELLE)

### ✅ Tâches Complétées

1. ✅ Lecture rapport grounding D3
2. ✅ Cartographie exhaustive tests/
3. ✅ Analyse structure imports (5 échantillons)
4. ✅ Identification matrice dépendances
5. ✅ Baseline pytest établie

### ⏳ Tâches Restantes

1. **Corriger erreur tiktoken**
   ```bash
   conda run -n projet-is-roo-new pip install tiktoken
   ```

2. **Enregistrer marqueurs pytest** dans `pytest.ini`

3. **Relancer baseline corrective**
   ```bash
   pytest -v --tb=short
   ```
   - Vérifier 0 erreur de collection
   - Documenter passed/failed/skipped
   - Confirmer état 100% opérationnel

4. **Obtenir validation utilisateur** pour démarrer Phase D3.1

---

## 📦 Phase D3.1 : Lots de Ventilation

### Stratégie Globale

**Objectif** : Réorganiser les tests en créant une structure claire et modulaire, en commençant par les zones à faible risque.

**Structure cible proposée** :
```
tests/
├── unit/                    # Tests unitaires isolés
│   ├── api/
│   ├── core/
│   ├── agents/
│   └── argumentation_analysis/
├── integration/             # Tests d'intégration système
├── e2e/                     # Tests end-to-end complets
├── functional/              # Tests fonctionnels
├── performance/             # Tests de performance
├── robustness/              # Tests de robustesse
├── fixtures/                # Fixtures partagées (NE PAS TOUCHER)
├── mocks/                   # Mocks et doubles de test
├── support/                 # Utilitaires de support pour tests
└── conftest.py              # Configuration globale (NE PAS TOUCHER)
```

---

### Lot 1 : Zone Mocks (Faible Risque) - PRIORITÉ 1

**Cible** : `tests/mocks/` (10-12 fichiers)

**Fichiers identifiés** (à confirmer par liste exacte) :
- `tests/mocks/test_jpype_mock.py` (isolé, safe)
- `tests/mocks/test_numpy_rec_mock.py`
- `tests/mocks/mock_*.py` (fichiers de mock purs)

**Action** :
1. Lister exactement les fichiers dans `tests/mocks/`
2. Identifier ceux qui sont des tests vs helpers
3. **Option A** : Si structure claire, conserver `tests/mocks/`
4. **Option B** : Si mélange, séparer en :
   - `tests/support/mocks/` (helpers)
   - Tests mockés dispersés vers catégories appropriées

**Validation** :
```bash
# Avant modification
pytest -v tests/mocks/ --tb=short

# Après modification
pytest -v tests/mocks/ --tb=short  # ou nouveau chemin
pytest -v --tb=short               # suite complète
```

**Commit** :
```
Phase D3.1 - Lot 1: Réorganisation tests/mocks/

- [Action détaillée]
- Baseline pytest: MAINTENUE
- Tests impactés: X fichiers
```

**Rollback plan** :
```bash
git tag phase-d3-pre-lot1
# Si échec: git reset --hard phase-d3-pre-lot1
```

---

### Lot 2 : Utils et Support (Faible Risque) - PRIORITÉ 2

**Cible** : `tests/dev_utils/`, `tests/utils/`, `tests/support/`

**Fichiers estimés** : ~15-20 fichiers

**Action** :
1. Consolider tous les utilitaires sous `tests/support/`
   ```
   tests/support/
   ├── dev_utils/      # Outils de développement
   ├── test_utils/     # Utilitaires de test
   └── helpers/        # Fonctions helper
   ```

2. Vérifier qu'aucun fichier n'est un "vrai" test (commence par `test_`)

3. Si tests trouvés, les déplacer vers catégorie appropriée

**Validation** :
```bash
pytest -v tests/support/ --tb=short
pytest -v --tb=short
```

**Commit atomique** (si > 15 fichiers, diviser en 2 commits)

**Rollback plan** : Tag git avant

---

### Lot 3 : Tests Unitaires Simples (Risque Modéré) - PRIORITÉ 3

**Cible** : Tests unitaires sans dépendances complexes

**Candidats** (à identifier précisément) :
- Tests dans `tests/unit/` qui n'importent PAS de fixtures complexes
- Tests avec imports directs uniquement
- Tests isolés identifiés dans la cartographie

**Volume** : 10-15 fichiers MAX

**Action** :
1. Analyser imports de chaque candidat
2. Vérifier absence de dépendance à `conftest.py` ou `fixtures/`
3. Si clean, organiser par module :
   ```
   tests/unit/
   ├── api/
   ├── core/
   ├── agents/
   └── utils/
   ```

**Validation** :
```bash
pytest -v tests/unit/[sous-répertoire] --tb=short
pytest -v --tb=short
```

**Commit** : Atomique par sous-catégorie

**Rollback plan** : Tag git avant chaque commit

---

### Lot 4 : Documentation et Configuration (Faible Risque) - PRIORITÉ 4

**Cible** : README.md, fichiers de configuration

**Fichiers** :
- `tests/README.md` (si existe)
- Fichiers `.gitignore`, `.gitkeep` (si existent)
- Documentation de tests

**Action** :
1. Créer/mettre à jour `tests/README.md` avec :
   - Structure des tests
   - Comment exécuter les tests
   - Convention de nommage
   - Stratégie mocks vs authentiques

2. Documenter les marqueurs pytest

**Validation** :
- Pas de pytest nécessaire (pas de code)
- Vérification manuelle de la documentation

**Commit** :
```
Phase D3.1 - Lot 4: Documentation tests/

- Création/mise à jour README.md
- Documentation structure et conventions
```

---

### Checkpoint SDDD après Lot 4

**Timing** : Après complétion des 4 premiers lots

**Action** :
1. Recherche sémantique sur "test organization" dans le projet
2. Vérifier cohérence avec documentation
3. Identifier patterns émergents
4. Ajuster stratégie pour lots suivants si nécessaire

**Outil** :
```
codebase_search: "test organization structure pytest"
```

**Livrable** : Note de checkpoint dans `.temp/cleanup_campaign_2025-10-03/02_phases/phase_D3/CHECKPOINT_LOT4.md`

---

### Lots 5-N : À Planifier Après Checkpoint

**Dépendant de** :
- Résultats des 4 premiers lots
- Feedback checkpoint SDDD
- Complexités découvertes

**Candidats potentiels** :
- Lot 5: Tests `comparison/` (risque modéré)
- Lot 6: Tests `environment_checks/` (risque modéré)
- Lot 7: Tests `validation/` (risque modéré)
- Lot 8-N: À définir progressivement

**Méthodologie** :
- Continuer par ordre de risque croissant
- Lots de 10-15 fichiers max
- Validation pytest systématique

---

## 🔍 Phase D3.2 : Consolidation (POST-VENTILATION)

**Démarrage** : Après complétion de tous les lots de ventilation

### Objectifs

1. **Audit de redondances**
   - Identifier tests en double
   - Fusionner tests similaires
   - Supprimer tests obsolètes

2. **Optimisation des imports**
   - Supprimer imports inutilisés
   - Standardiser patterns d'imports
   - Corriger imports conditionnels si possible

3. **Normalisation des marqueurs**
   - Enregistrer TOUS les marqueurs dans `pytest.ini`
   - Appliquer marqueurs cohérents
   - Documenter usage des marqueurs

### Candidats à la Suppression (à valider)

**Critères** :
- Tests commentés depuis longtemps
- Tests avec `@pytest.mark.skip` permanent
- Fichiers de test vides ou quasi-vides
- Doublons évidents

**Processus** :
1. Identifier candidats
2. Recherche sémantique pour confirmer obsolescence
3. **Validation utilisateur OBLIGATOIRE** avant suppression
4. Suppression avec git tag de sécurité

**Documentation** : Liste dans `.temp/cleanup_campaign_2025-10-03/02_phases/phase_D3/CANDIDATS_SUPPRESSION.md`

---

## 🛠️ Phase D3.3 : Optimisation Fixtures (CRITIQUE)

**Démarrage** : UNIQUEMENT après validation complète Phase D3.2

**⚠️ ATTENTION** : Zone à TRÈS HAUT RISQUE

### Pré-requis ABSOLUS

1. ✅ Baseline pytest 100% stable
2. ✅ Aucun test en régression depuis D3.1
3. ✅ Documentation complète de l'utilisation des fixtures
4. ✅ Validation utilisateur explicite avant CHAQUE action

### Audit conftest.py

**Objectifs** :
1. Documenter toutes les fixtures
2. Identifier fixtures inutilisées
3. Repérer potentiels de refactoring

**Action** :
```python
# Audit à effectuer (sans modification)
1. Liste toutes les fixtures dans conftest.py
2. Pour chaque fixture:
   - Scope (session/module/function)
   - Fichiers qui l'utilisent
   - Fréquence d'utilisation
3. Identifier dépendances entre fixtures
```

**Livrable** : `.temp/cleanup_campaign_2025-10-03/02_phases/phase_D3/AUDIT_FIXTURES.md`

### Actions UNIQUEMENT si Nécessaire et Validé

**Scénarios possibles** :
1. **Fixture inutilisée** → Conserver avec marqueur deprecated
2. **Fixture dupliquée** → Fusionner AVEC EXTRÊME PRUDENCE
3. **Fixture sur-utilisée** → Possibilité de refactoring

**Règle d'or** : En cas de doute, **NE PAS MODIFIER**

---

## 🔬 Checkpoints SDDD Prévus

### Checkpoint 1 : Après Lot 4 (Initial)
- **Timing** : Après 4 premiers lots
- **Focus** : Validation stratégie de base
- **Livrable** : CHECKPOINT_LOT4.md

### Checkpoint 2 : Mi-Ventilation
- **Timing** : Après ~50% des lots planifiés
- **Focus** : Ajustement stratégie si nécessaire
- **Livrable** : CHECKPOINT_MID_D3.1.md

### Checkpoint 3 : Pré-Consolidation
- **Timing** : Avant démarrage Phase D3.2
- **Focus** : Validation complète ventilation
- **Livrable** : CHECKPOINT_PRE_D3.2.md

### Checkpoint 4 : Pré-Fixtures
- **Timing** : Avant toute action sur fixtures
- **Focus** : Sécurité maximale
- **Livrable** : CHECKPOINT_PRE_FIXTURES.md

### Checkpoint 5 : Final
- **Timing** : Fin Phase D3
- **Focus** : Validation exhaustive
- **Livrable** : RAPPORT_FINAL_D3.md

---

## ✅ Critères de Succès Phase D3

### Critères Techniques

1. **Baseline pytest maintenue**
   - ✅ Aucun test en régression
   - ✅ Nombre de tests constant ou augmenté (si split)
   - ✅ Temps d'exécution stable ou amélioré
   - ✅ 0 nouvelle erreur de collection

2. **Structure claire et logique**
   - ✅ Organisation par type de test
   - ✅ Séparation tests/fixtures/mocks/support
   - ✅ Conventions de nommage respectées

3. **Documentation à jour**
   - ✅ README.md complet
   - ✅ Marqueurs pytest enregistrés
   - ✅ Guide d'utilisation pour développeurs

4. **Commits atomiques**
   - ✅ Maximum 15 fichiers par commit
   - ✅ Messages descriptifs
   - ✅ Validation pytest systématique
   - ✅ Tags git de sécurité

### Critères Qualité

1. **Maintenabilité**
   - ✅ Structure intuitive
   - ✅ Tests faciles à localiser
   - ✅ Dépendances claires

2. **Performance**
   - ✅ Pas de régression temps d'exécution
   - ✅ Amélioration possible (bonus)

3. **Robustesse**
   - ✅ Tests isolés quand possible
   - ✅ Dépendances minimisées
   - ✅ Fixtures documentées

---

## 🚨 Signaux d'Alerte et Actions

### 🔴 ALERTE CRITIQUE : STOP IMMÉDIAT

**Déclencheurs** :
- Pytest échoue après modification
- Tests précédemment réussis deviennent skipped
- Import errors apparaissent
- JVM se bloque

**Action** :
1. ❌ **STOP** toute modification
2. 📝 Documenter le problème
3. 🔙 **ROLLBACK** immédiat au tag git
4. 🤝 Validation utilisateur avant reprise

### 🟡 ALERTE MODÉRÉE : PRÉCAUTION

**Déclencheurs** :
- Augmentation significative du temps d'exécution (>10%)
- Nouveaux warnings pytest
- Tests skippés inattendus

**Action** :
1. ⏸️ Pause pour investigation
2. 📊 Analyser les causes
3. 📝 Documenter les observations
4. 🤔 Décider : continuer, ajuster, ou rollback

### 🟢 VERT : Tout va bien

**Indicateurs** :
- Pytest passe (0 fail, 0 error)
- Nombre tests stable
- Temps exécution stable
- Aucun nouveau warning critique

**Action** :
- ✅ Continuer selon plan
- 📝 Documenter succès
- ⏭️ Passer au lot suivant

---

## 📋 Prochaines Actions Immédiates

### Avant Démarrage Phase D3.1

1. **Corriger baseline**
   - [ ] Installer tiktoken
   - [ ] Enregistrer marqueurs pytest.ini
   - [ ] Relancer pytest complet
   - [ ] Confirmer 0 erreur

2. **Validation utilisateur**
   - [ ] Présenter cette stratégie
   - [ ] Obtenir feu vert explicite
   - [ ] Clarifier zones d'incertitude

3. **Préparation technique**
   - [ ] Créer branche dédiée `cleanup/phase-d3`
   - [ ] Tag git initial `phase-d3-start`
   - [ ] Préparer logs de suivi

### Démarrage Lot 1

1. **Grounding sémantique**
   ```
   codebase_search: "mock strategy test doubles"
   ```

2. **Liste fichiers exacte**
   ```bash
   ls -la tests/mocks/
   ```

3. **Analyse dépendances**
   - Vérifier imports de chaque fichier
   - Confirmer isolation

4. **Exécution**
   - Suivre plan Lot 1
   - Validation pytest après chaque action

---

## 📚 Références

- **CARTOGRAPHIE_TESTS.md** : Inventaire complet et analyse structure
- **BASELINE_PYTEST.md** : État de référence pytest
- **RAPPORT_GROUNDING_D3.md** : Recherches sémantiques initiales
- **pytest.ini** : Configuration pytest actuelle

---

**Version** : 1.0  
**Date** : 2025-10-14  
**Status** : 🟡 EN ATTENTE VALIDATION UTILISATEUR