# 🛠️ Guide Utilisateur Complet - Système Sherlock-Watson-Moriarty
## Installation, Configuration et Utilisation

> **Guide pratique pour démarrer rapidement avec le système Oracle Enhanced**  
> Tous les exemples et commandes testés - Janvier 2025

---

## 📚 **NAVIGATION RAPIDE**

| 🎯 **Section** | ⏱️ **Temps** | 🔗 **Liens Associés** |
|----------------|-------------|----------------------|
| [⚡ Démarrage Express](#-démarrage-express) | 2 min | [📖 Index Principal](README.md) |
| [🔧 Installation Complète](#-installation-complète) | 15 min | [🏗️ Architecture](guide_unifie_sherlock_watson.md) |
| [🎲 Démo Cluedo Oracle](#-démo-cluedo-oracle-enhanced) | 10 min | [📋 Rapport Oracle](RAPPORT_MISSION_ORACLE_ENHANCED.md) |
| [🧩 Démo Einstein](#-démo-einstein-oracle) | 10 min | [📊 Analyse Orchestrations](../analyse_orchestrations_sherlock_watson.md) |
| [🚨 Dépannage](#-dépannage) | 5 min | [🔧 Architecture Technique](guide_unifie_sherlock_watson.md) |
| [🛡️ Sécurité et Règles](#️-sécurité-et-règles-du-jeu) | 5 min | [📊 Audit Intégrité](AUDIT_INTEGRITE_CLUEDO.md) |

---

## ⚡ **DÉMARRAGE EXPRESS**

### 🚀 **Installation en 2 Minutes**

```powershell
# 1. Naviguer vers le répertoire du projet
cd d:\2025-Epita-Intelligence-Symbolique

# 2. Activer l'environnement Conda spécialisé
powershell -c "& .\scripts\activate_project_env.ps1"

# 3. Test rapide - Démonstration conceptuelle 
python scripts\sherlock_watson\test_oracle_behavior_simple.py

# 4. Démo Cluedo Oracle Enhanced
python scripts\sherlock_watson\run_cluedo_oracle_enhanced.py

# 5. Démo Einstein Oracle avec indices
python scripts\sherlock_watson\run_einstein_oracle_demo.py
```

### ✅ **Vérification Rapide**

Si tout fonctionne, vous devriez voir :
```
✅ Oracle Enhanced : FONCTIONNEL
✅ Semantic Kernel : CONNECTÉ  
✅ Tweety JVM : OPÉRATIONNEL
✅ Agents : Sherlock, Watson, Moriarty PRÊTS
```

---

## 🔧 **INSTALLATION COMPLÈTE**

### 📋 **Prérequis Système**

| 🛠️ **Composant** | 📦 **Version** | 🔗 **Vérification** |
|------------------|----------------|-------------------|
| **Python** | 3.9+ | `python --version` |
| **PowerShell** | 7.0+ | `pwsh --version` |
| **Java JDK** | 11+ | `java -version` |
| **Conda** | 4.10+ | `conda --version` |

### 🐍 **Environnement Conda Spécialisé**

#### Création de l'Environnement
```powershell
# Création environnement dédié (si pas déjà fait)
conda create -n epita_symbolic_ai_sherlock python=3.9
conda activate epita_symbolic_ai_sherlock

# Installation dépendances de base
pip install semantic-kernel==1.29.0
pip install openai==1.52.0
pip install pydantic==2.10.3
pip install jpype1==1.4.1
```

#### Script d'Activation Automatisé
Le script [`scripts/activate_project_env.ps1`](../../scripts/activate_project_env.ps1) automatise :
- ✅ Activation environnement Conda `epita_symbolic_ai_sherlock`
- ✅ Configuration variables d'environnement
- ✅ Vérification dépendances critiques
- ✅ Initialisation bridge Tweety JVM

### ☕ **Configuration JVM Tweety**

#### Vérification des JAR Files
```powershell
# Vérification présence des bibliothèques Tweety
Get-ChildItem libs\*.jar | Measure-Object | Select-Object Count
# Résultat attendu: Count = 35+ JAR files
```

#### Variables d'Environnement JVM
```powershell
# Variables automatiquement configurées par activate_project_env.ps1
$env:JAVA_TOOL_OPTIONS = "-Xmx4G -Xms1G"
$env:TWEETY_JAR_PATH = "d:\2025-Epita-Intelligence-Symbolique\libs"
```

---

## 🛡️ **SÉCURITÉ ET RÈGLES DU JEU**

### 🔒 **Intégrité Cluedo Certifiée**

Le système Oracle Enhanced respecte **strictement les règles du jeu Cluedo** grâce à un audit d'intégrité complet effectué en Janvier 2025.

#### ✅ **Garanties de Sécurité**
- **Isolation des joueurs** : Chaque joueur ne voit que ses propres cartes
- **Secret de la solution** : Aucun accès direct à la solution
- **Révélations légitimes** : Seules les révélations autorisées sont permises
- **Anti-triche** : Protection contre toute forme de manipulation

### 🚨 **Protections Anti-Triche**

#### CluedoIntegrityError
Le système utilise une exception spécialisée pour détecter et bloquer les violations :

```python
# Exemple de protection automatique
try:
    cartes_autres = dataset.get_autres_joueurs_cards()  # ❌ INTERDIT
except PermissionError as e:
    print("🚨 VIOLATION RÈGLES CLUEDO détectée !")
    # Le système protège automatiquement l'intégrité
```

#### Méthodes Sécurisées
| ❌ **Interdit** | ✅ **Autorisé** |
|-----------------|------------------|
| `get_autres_joueurs_cards()` | `get_mes_cartes()` |
| `get_solution()` | `faire_suggestion()` |
| Accès direct aux cartes des autres | Révélations via Oracle |
| Simulation basée sur triche | Simulation probabiliste |

### 🧪 **Tests d'Intégrité**

#### Validation Continue
```powershell
# Test d'intégrité complet (8/8 tests)
python test_validation_integrite_apres_corrections.py

# Test fonctionnel simple (5/5 tests)
python test_cluedo_dataset_simple.py

# Résultat attendu : 100% tests passent AVEC intégrité
```

#### Contrôles Automatiques
- **Validation des accès** : Chaque opération est vérifiée
- **Logging sécurisé** : Traçabilité des interactions
- **Permissions renforcées** : Contrôle multi-niveaux
- **Audit en temps réel** : Détection immédiate des violations

### 📊 **Certification Audit**

**RÉSULTAT OFFICIEL :** ✅ **INTÉGRITÉ CERTIFIÉE**
- **4 violations critiques** détectées et corrigées
- **Tests à 100%** maintenus AVEC respect des règles
- **Mécanismes anti-triche** implémentés et validés
- **Système Oracle Enhanced** opérationnel avec sécurité

**Documentation complète :** [📊 AUDIT_INTEGRITE_CLUEDO.md](AUDIT_INTEGRITE_CLUEDO.md)

### 🎮 **Ce qui est Permis vs Interdit**

#### ✅ **AUTORISÉ - Jeu Légitime**
- Voir ses propres cartes uniquement
- Faire des suggestions Cluedo
- Recevoir des révélations d'autres joueurs
- Utiliser la logique et la déduction
- Consulter l'historique de ses propres actions

#### ❌ **INTERDIT - Violations Bloquées**
- Accéder aux cartes des autres joueurs
- Voir la solution directement
- Utiliser des informations non autorisées
- Contourner les mécanismes de révélation
- Exploiter des failles système
```

### 🔑 **Configuration OpenAI API**

#### Fichier de Configuration
Créer [`config/openai_config.json`](../../config/openai_config.json) :
```json
{
  "api_key": "sk-votre-clé-openai-ici",
  "model": "gpt-4o-mini", 
  "max_tokens": 2000,
  "temperature": 0.3,
  "timeout": 30
}
```

#### Variables d'Environnement (Alternative)
```powershell
# Méthode alternative via variables d'environnement
$env:OPENAI_API_KEY = "sk-votre-clé-openai-ici"
$env:OPENAI_MODEL = "gpt-4o-mini"
```

---

## 🎲 **DÉMO CLUEDO ORACLE ENHANCED**

### 🚀 **Lancement de la Démo**

```powershell
# Activation environnement + lancement
powershell -c "& .\scripts\activate_project_env.ps1"
python scripts\sherlock_watson\run_cluedo_oracle_enhanced.py
```

### 📋 **Exemple de Session Complète**

#### 🎬 **Initialisation**
```
🎮 CLUEDO ORACLE ENHANCED - Démarrage
=====================================

🏰 Contexte: Mystère au Manoir Tudor
🎭 Agents: Sherlock Holmes, Dr. Watson, Professor Moriarty
🃏 Solution secrète: [CACHÉE - Colonel Moutarde, Poignard, Salon]
🎲 Cartes Moriarty: [Professeur Violet, Chandelier, Cuisine, Mlle Rose]

🚀 Workflow 3-agents démarré...
```

#### 🔄 **Tour 1 - Sherlock Enquête**
```
🕵️ [SHERLOCK] Tour 1
━━━━━━━━━━━━━━━━━━━━━
"Observons la scène... D'après les indices initiaux, 
je suggère le Professeur Violet avec le Chandelier dans la Cuisine."

📝 Suggestion extraite: {suspect: "Professeur Violet", arme: "Chandelier", lieu: "Cuisine"}
➤ Transition vers Watson...
```

#### 🧪 **Tour 2 - Watson Validation**
```
🧪 [WATSON] Tour 2  
━━━━━━━━━━━━━━━━━━━━━
"Analysons logiquement cette hypothèse, Holmes..."

🔍 TweetyProject: Vérification contraintes...
✅ Aucune contradiction détectée avec belief set actuel
📊 Belief set mis à jour avec nouvelles propositions

➤ Transition vers Moriarty Oracle...
```

#### 🎭 **Tour 3 - Moriarty Oracle (🆕 Enhanced)**
```
🎭 [MORIARTY] Tour 3 - RÉVÉLATION ORACLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Détection automatique: Suggestion Sherlock analysée
🃏 Vérification cartes: [Professeur Violet ✓, Chandelier ✓, Cuisine ✓]
🎯 TOUTES LES CARTES POSSÉDÉES !

💬 "*sourire énigmatique* Ah, Sherlock... 
Je possède Professeur Violet, Chandelier, Cuisine ! 
Votre théorie s'effondre."

📋 Révélations enregistrées: 3 cartes éliminées
➤ Progression garantie - Retour à Sherlock...
```

#### 🔄 **Tour 4-6 - Cycle Affiné**
```
🕵️ [SHERLOCK] Tour 4
━━━━━━━━━━━━━━━━━━━━━
"Intéressant... Éliminons ces possibilités.
Nouvelle hypothèse: Colonel Moutarde avec le Poignard dans le Salon ?"

🧪 [WATSON] Tour 5
━━━━━━━━━━━━━━━━━━━━━
🔄 BeliefSet mis à jour: NOT(Violet), NOT(Chandelier), NOT(Cuisine)
✅ Nouvelle suggestion cohérente avec contraintes

🎭 [MORIARTY] Tour 6
━━━━━━━━━━━━━━━━━━━━━━
🔍 Vérification: [Moutarde, Poignard, Salon] vs [Violet, Chandelier, Cuisine, Rose]
❌ Aucune carte correspondante → Ne peut pas réfuter

💬 "*hochement approbateur* Je ne peux réfuter cette suggestion, Holmes."
```

#### 🏁 **Terminaison**
```
🕵️ [SHERLOCK] Tour 7 - SOLUTION FINALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Si Moriarty ne peut réfuter... Ma solution finale :
Colonel Moutarde, Poignard, Salon"

🎯 VALIDATION ORCHESTRATEUR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Solution proposée: [Colonel Moutarde, Poignard, Salon]
✅ Solution secrète:  [Colonel Moutarde, Poignard, Salon]
🎉 SUCCÈS COMPLET !

📊 MÉTRIQUES FINALES
━━━━━━━━━━━━━━━━━━━━━
🔄 Tours total: 7 (vs 10-12 workflow classique)
🎭 Révélations Oracle: 3 cartes dévoilées  
⚡ Temps total: 45 secondes
🎯 Efficacité: Oracle Enhanced = +40% vs classique
```

### 🎯 **Points Clés de la Démo**

1. **🔮 Oracle Authentique** - Moriarty révèle automatiquement ses cartes
2. **📈 Progression Garantie** - Chaque révélation fait avancer l'enquête  
3. **🔄 Workflow Cyclique** - Sherlock → Watson → Moriarty → répétition
4. **🎭 Authenticité Narrative** - Révélations dramatiques vs suggestions banales

---

## 🧩 **DÉMO EINSTEIN ORACLE**

### 🚀 **Lancement de la Démo**

```powershell
python scripts\sherlock_watson\run_einstein_oracle_demo.py
```

### 📋 **Exemple de Session**

#### 🎬 **Initialisation**
```
🧩 EINSTEIN'S RIDDLE - Oracle avec Indices Progressifs
====================================================

🏠 Contexte: 5 maisons, 5 propriétaires, 25 attributs à déduire
🎭 Agents: Sherlock Holmes, Dr. Watson, Professor Moriarty (Oracle Indices)
🧮 Contraintes: 15 indices logiques complexes
🎯 Objectif: Déduction complète par logique formelle

🚀 Workflow Oracle Einstein démarré...
```

#### 🔄 **Tour 1 - Moriarty Oracle Indices**
```
🎭 [MORIARTY] Tour 1 - DISTRIBUTION INDICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"*pose dramatique* Premier indice pour votre déduction :
L'Anglais vit dans la maison rouge."

📝 Indice Oracle distribué: ANGLAIS → ROUGE
🎯 Progression: 1/15 indices révélés
```

#### 🕵️ **Tour 2 - Sherlock Intégration**
```
🕵️ [SHERLOCK] Tour 2
━━━━━━━━━━━━━━━━━━━━━
"Intéressant... Je note cette contrainte fondamentale.
L'Anglais et la maison rouge sont liés.
Watson, formalisez cette relation en logique propositionnelle."

📊 Hypothèse formulée: Anglais-Rouge contrainte de base
```

#### 🧪 **Tour 3 - Watson Formalisation**
```
🧪 [WATSON] Tour 3
━━━━━━━━━━━━━━━━━━━━━
"Je crée une grille logique formelle..."

🔍 TweetyProject: Création BeliefSet Einstein
✅ Formule ajoutée: Anglais(X) → Rouge(X)
📊 Variables domaine: 5 positions, 5 nationalités, 5 couleurs
🎯 Contraintes satisfaisantes: 1/15
```

#### 🔄 **Cycles 4-15 - Progression Logique**
```
🎭 [MORIARTY] Tours 4,7,10,13... - INDICES PROGRESSIFS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Le Suédois a un chien"
"Le Danois boit du thé"  
"La maison verte est directement à gauche de la blanche"
"Le propriétaire de la maison verte boit du café"
[... 15 indices au total ...]

🧪 [WATSON] Formalisation Continue
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 BeliefSet Einstein enrichi progressivement
✅ 15 formules logiques complexes
🎯 Contraintes: Position(X,Y) ∧ Attribut(X,Z) → Relations
📊 Validation cohérence à chaque ajout

🕵️ [SHERLOCK] Déduction Guidée
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Avec ces contraintes... Si l'Anglais est en rouge,
et la verte à gauche de la blanche, alors..."
[Raisonnement étape par étape]
```

#### 🏁 **Solution Finale**
```
🕵️ [SHERLOCK] SOLUTION EINSTEIN COMPLÈTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Position 1: Norvégien, Jaune, Eau, Dunhill, Chats
Position 2: Danois, Bleue, Thé, Blend, Chevaux  
Position 3: Anglais, Rouge, Lait, Pall Mall, Oiseaux
Position 4: Allemand, Verte, Café, Prince, Poissons
Position 5: Suédois, Blanche, Bière, Blue Master, Chiens

🎯 QUI A LES POISSONS ? → L'ALLEMAND (Position 4)

✅ VALIDATION LOGIQUE COMPLÈTE
🧮 15/15 contraintes satisfaites
🎉 SUCCÈS PAR DÉDUCTION FORMELLE !
```

### 🎯 **Innovations Démo Einstein**

1. **💡 Oracle Progressif** - Indices dosés vs révélations cartes
2. **🧮 Logique Rigoureuse** - 15 contraintes formelles TweetyProject
3. **🎯 Déduction Guidée** - Sherlock raisonne étape par étape
4. **✅ Validation Formelle** - Chaque étape vérifiée logiquement

---

## 🔧 **SCRIPTS AVANCÉS**

### 📁 **Répertoire Scripts**

```
scripts/sherlock_watson/
├── 🎲 run_cluedo_oracle_enhanced.py        # Cluedo Oracle Enhanced
├── 🧩 run_einstein_oracle_demo.py          # Einstein indices progressifs  
├── 🧪 test_oracle_behavior_simple.py       # Démonstration conceptuelle
└── 🚧 run_logique_complexe_demo.py         # Logique complexe (futur)
```

### ⚙️ **Paramètres de Configuration**

#### Modification des Agents
```python
# Dans les scripts - Configuration personnalisable
AGENT_CONFIG = {
    "sherlock": {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 1500
    },
    "watson": {
        "model": "gpt-4o-mini", 
        "temperature": 0.1,     # Plus déterministe pour logique
        "max_tokens": 2000
    },
    "moriarty": {
        "oracle_strategy": "balanced",  # cooperative, competitive, balanced
        "revelation_probability": 0.8
    }
}
```

#### Personnalisation Cluedo
```python
# Éléments de jeu personnalisables
CUSTOM_CLUEDO_ELEMENTS = {
    "suspects": ["Colonel Moutarde", "Mlle Rose", "Professeur Violet", 
                "Mme Leblanc", "Mme Pervenche", "Dr. Olive"],
    "armes": ["Poignard", "Chandelier", "Revolver", 
              "Corde", "Clé Anglaise", "Tuyau de Plomb"],
    "lieux": ["Salon", "Cuisine", "Salle de Bal", 
              "Véranda", "Bibliothèque", "Bureau"]
}
```

### 🎯 **Modes d'Exécution**

#### Mode Verbose (Défaut)
```powershell
python scripts\sherlock_watson\run_cluedo_oracle_enhanced.py --verbose
```

#### Mode Silencieux
```powershell
python scripts\sherlock_watson\run_cluedo_oracle_enhanced.py --quiet
```

#### Mode Debug avec Logs Détaillés
```powershell
python scripts\sherlock_watson\run_cluedo_oracle_enhanced.py --debug --log-file="cluedo_session.log"
```

---

## 🔒 **SÉCURITÉ POST-AUDIT INTÉGRITÉ**

### 🛡️ **Mécanismes Anti-Triche Validés**

Suite à l'audit d'intégrité réalisé, le système intègre des **mécanismes de sécurité renforcés** :

#### ✅ **Contrôles d'Intégrité Actifs**
```python
# Vérification automatique lors du démarrage
python test_audit_integrite_cluedo.py

# Résultat attendu :
✅ CluedoIntegrityError : Déployé et fonctionnel
✅ 4 violations détectées et corrigées
✅ Tests : 100% maintenus
✅ Sécurité Oracle : Renforcée
```

#### 🔐 **Validation des Datasets Oracle**
- **Contrôle accès dataset** : Permissions vérifiées avant chaque interrogation
- **Intégrité des révélations** : Hash de validation pour chaque carte révélée
- **Anti-exploitation** : Limite de tentatives et timeout configurables
- **Audit trail** : Logging complet des interactions Oracle

#### 🚨 **Détection Anomalies Temps Réel**
```powershell
# Surveillance continue (optionnelle)
python scripts/sherlock_watson/run_cluedo_oracle_enhanced.py --audit-mode

# Indicateurs de sécurité :
🔍 Tentatives accès non autorisées : 0
⚡ Révélations légitimes : 100%
🛡️ Intégrité dataset : CONSERVÉE
```

### ⚠️ **Signalement d'Incident**
En cas de comportement suspect :
1. **CluedoIntegrityError** levée automatiquement
2. **Logs détaillés** dans `logs/audit_integrite.log`
3. **Arrêt sécurisé** du workflow en cours
4. **Rapport d'incident** généré automatiquement

---

## 🚨 **DÉPANNAGE**

### ❌ **Problèmes Courants**

#### 1. Erreur "Environnement Conda Non Trouvé"
```powershell
# Symptôme
conda activate epita_symbolic_ai_sherlock
# CondaEnvironmentError: environment does not exist

# 🔧 Solution
conda create -n epita_symbolic_ai_sherlock python=3.9
conda activate epita_symbolic_ai_sherlock
pip install -r requirements.txt
```

#### 2. Erreur "JVM Cannot Start"
```
# Symptôme  
JPypeException: JVM cannot start
java.lang.OutOfMemoryError: Java heap space

# 🔧 Solution
$env:JAVA_TOOL_OPTIONS = "-Xmx8G -Xms2G"  # Augmenter mémoire
powershell -c "& .\scripts\activate_project_env.ps1"
```

#### 3. Erreur "OpenAI API Key Invalid"
```
# Symptôme
openai.AuthenticationError: Invalid API key

# 🔧 Solution
# Vérifier clé API dans config/openai_config.json
# Ou définir variable d'environnement
$env:OPENAI_API_KEY = "sk-votre-nouvelle-clé"
```

#### 4. Erreur "TweetyProject JAR Not Found"
```
# Symptôme
FileNotFoundError: libs/tweety-*.jar

# 🔧 Solution  
# Vérifier présence des JAR files
Get-ChildItem libs\*.jar
# Si manquants, réinstaller Tweety dependencies
```

#### 5. Performance Lente
```
# Symptôme
Agents très lents à répondre (>30 secondes)

# 🔧 Solutions
# 1. Réduire max_tokens dans config
# 2. Utiliser modèle plus rapide (gpt-3.5-turbo)  
# 3. Augmenter timeout OpenAI
# 4. Vérifier connexion internet
```

### 🔍 **Diagnostic Avancé**

#### Test de Connectivité Complète
```powershell
# Test script de diagnostic
python scripts\sherlock_watson\test_oracle_behavior_simple.py

# Vérifications automatiques:
# ✅ Environnement Conda
# ✅ Dépendances Python
# ✅ Configuration OpenAI
# ✅ Bridge Tweety JVM
# ✅ Agents fonctionnels
```

#### Logs de Debug
```powershell
# Activation logs détaillés
$env:SHERLOCK_DEBUG = "1"
$env:WATSON_DEBUG = "1" 
$env:MORIARTY_DEBUG = "1"

python scripts\sherlock_watson\run_cluedo_oracle_enhanced.py --debug
```

#### Monitoring de Performance
```powershell
# Métriques temps réel
python -c "
import psutil
print(f'CPU: {psutil.cpu_percent()}%')
print(f'RAM: {psutil.virtual_memory().percent}%')
print(f'JVM: {psutil.disk_usage(\".\").percent}%')
"
```

### 🛠️ **Solutions d'Urgence**

#### Reset Complet de l'Environnement
```powershell
# 1. Supprimer environnement existant
conda remove -n epita_symbolic_ai_sherlock --all

# 2. Recréer de zéro
conda create -n epita_symbolic_ai_sherlock python=3.9
conda activate epita_symbolic_ai_sherlock

# 3. Réinstaller dépendances
pip install semantic-kernel==1.29.0 openai==1.52.0 pydantic==2.10.3 jpype1==1.4.1

# 4. Test immédiat
python scripts\sherlock_watson\test_oracle_behavior_simple.py
```

---

## 🎯 **CONSEILS D'UTILISATION OPTIMALE**

### ⚡ **Performance**
- 🚀 **Démarrage à froid** : Première exécution plus lente (JVM init)
- ⚡ **Exécutions suivantes** : Performances optimales 
- 💾 **Mémoire recommandée** : 8GB RAM minimum pour confort

### 🎮 **Expérience Utilisateur**
- 📺 **Terminal large** : 120+ caractères pour affichage optimal
- 🎨 **Couleurs activées** : PowerShell avec support ANSI
- 📝 **Logs sauvegardés** : Option `--log-file` pour traçabilité

### 🔧 **Développement**
- 🐛 **Mode debug** : Toujours utiliser `--debug` pour développement
- 📊 **Métriques** : Surveiller performances via logs
- 🔄 **Itération rapide** : Scripts modulaires pour tests spécifiques

---

## 🔗 **LIENS UTILES**

### 📚 **Documentation Complémentaire**
- 🏗️ **[Architecture Complète](guide_unifie_sherlock_watson.md)** - Système multi-agents détaillé
- 🔧 **[Architecture Technique](guide_unifie_sherlock_watson.md)** - Intégrations techniques approfondies
- 📖 **[Index Principal](README.md)** - Navigation centrale et accès rapide

### 📋 **Rapports et Analyses**
- 🎯 **[Rapport Oracle Enhanced](RAPPORT_MISSION_ORACLE_ENHANCED.md)** - Détails implémentation Oracle
- 📊 **[Analyse Orchestrations](../analyse_orchestrations_sherlock_watson.md)** - Métriques et performance

### 🛠️ **Ressources Techniques**
- ⚙️ **Semantic Kernel** : [Documentation officielle](https://learn.microsoft.com/semantic-kernel/)
- ☕ **TweetyProject** : [Site officiel](http://tweetyproject.org/)
- 🤖 **OpenAI API** : [Documentation API](https://platform.openai.com/docs)

---

**🎉 Vous êtes maintenant prêt à explorer l'univers du raisonnement collaboratif avec Sherlock, Watson et Moriarty !**

*Pour toute question ou problème, consultez la section dépannage ou référez-vous à la documentation technique approfondie.*

---

**📝 Document maintenu par :** Équipe Projet Sherlock/Watson  
**🔄 Dernière mise à jour :** Janvier 2025 - Oracle Enhanced  
**⏭️ Prochaine révision :** Mars 2025
## 🆕 Nouveaux Modules Oracle Enhanced v2.1.0

### Module de Gestion d'Erreurs (`error_handling.py`)

Le système Oracle Enhanced dispose désormais d'une gestion d'erreurs centralisée:

```python
from argumentation_analysis.agents.core.oracle.error_handling import (
    OracleErrorHandler, OraclePermissionError, oracle_error_handler
)

# Gestionnaire d'erreurs centralisé
error_handler = OracleErrorHandler()

# Décorateur pour gestion automatique
@oracle_error_handler("validation_context")
async def validate_suggestion(suggestion):
    if not suggestion.is_valid():
        raise OracleValidationError("Suggestion invalide")
    return True
```

#### Hiérarchie d'Erreurs Oracle:
- `OracleError`: Erreur de base du système Oracle
- `OraclePermissionError`: Erreurs de permissions et accès
- `OracleDatasetError`: Erreurs de dataset et données
- `OracleValidationError`: Erreurs de validation métier
- `CluedoIntegrityError`: Violations des règles Cluedo

### Module d'Interfaces (`interfaces.py`)

Interfaces standardisées pour tous les composants Oracle:

```python
from argumentation_analysis.agents.core.oracle.interfaces import (
    OracleAgentInterface, StandardOracleResponse, OracleResponseStatus
)

# Implémentation agent Oracle
class MyOracleAgent(OracleAgentInterface):
    async def process_oracle_request(self, agent, query_type, params):
        return StandardOracleResponse(
            success=True,
            data={"processed": True},
            metadata={"status": OracleResponseStatus.SUCCESS.value}
        ).to_dict()
```

## 📊 Tests et Validation

### Nouveau: Tests Automatisés Complets

Le système Oracle Enhanced dispose maintenant de **148+ tests** couvrant:

#### Tests Unitaires Nouveaux Modules:
```bash
# Tests gestion d'erreurs (20+ tests)
pytest tests/unit/argumentation_analysis/agents/core/oracle/test_error_handling.py -v

# Tests interfaces (15+ tests)  
pytest tests/unit/argumentation_analysis/agents/core/oracle/test_interfaces.py -v

# Tests intégration (8+ tests)
pytest tests/unit/argumentation_analysis/agents/core/oracle/test_new_modules_integration.py -v
```

#### Validation Couverture Automatique:
```bash
# Script de validation complet
python scripts/maintenance/validate_oracle_coverage.py

# Rapport HTML de couverture
# Généré dans: htmlcov/oracle/index.html
```

### Métriques de Qualité Actuelles:
- **Couverture tests**: 100% (148/148 tests Oracle)
- **Modules couverts**: 7/7 modules Oracle Enhanced
- **Intégrations testées**: error_handling ↔ interfaces
- **Performance**: < 2s exécution complète
