# 🚀 GUIDE DE DÉMARRAGE RAPIDE
## PROJET EPITA INTELLIGENCE SYMBOLIQUE - VERSION FINALE

**⚡ Configuration et test en 5 minutes**

---

## 🎯 **SETUP ULTRA-RAPIDE**

### **1. Installation Base (2 minutes)**
```bash
# Clonage et setup environnement
git clone <repository-url>
cd 2025-Epita-Intelligence-Symbolique-4
conda create --name projet-is python=3.9
conda activate projet-is
pip install -r requirements.txt
```

### **2. Configuration API OpenRouter (1 minute)**
```bash
# Créer fichier .env avec votre clé API
echo "OPENROUTER_API_KEY=sk-or-v1-VOTRE_CLE_ICI" > .env
echo "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1" >> .env
echo "OPENROUTER_MODEL=gpt-4o-mini" >> .env
```

**Obtenir une clé** : [OpenRouter.ai](https://openrouter.ai) → S'inscrire → Générer clé API

### **3. Test de Validation (2 minutes)**
```bash
# Test système complet
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```

---

## 🏆 **5 POINTS D'ENTRÉE VALIDÉS**

### **🎭 Point 1 - Démo Interactive**
```bash
python examples/scripts_demonstration/demonstration_epita.py --interactive
```
**Résultat** : Menu interactif avec 5 catégories d'exploration

### **⚙️ Point 2 - Système Rhétorique**
```bash
python argumentation_analysis/run_orchestration.py --interactive
```
**Résultat** : Analyse argumentative avec framework unifié

### **🕵️ Point 3 - Agents Sherlock/Watson/Moriarty**
```bash
python -m scripts.sherlock_watson.run_cluedo_oracle_enhanced
```
**Résultat** : Système multi-agents avec LLMs réels

### **🌐 Point 4 - Applications Web**
```bash
python start_webapp.py
```
**Résultat** : Interface web avec backend API

### **🧪 Point 5 - Tests avec LLMs Réels**
```bash
python -m pytest tests/unit/argumentation_analysis/test_strategies_real.py -v
```
**Résultat** : 400+ tests unitaires avec vrais appels gpt-4o-mini

---

## 📊 **VALIDATION IMMÉDIATE**

### **✅ Système Fonctionnel**
- [x] Python 3.9+ installé
- [x] Dépendances installées
- [x] API OpenRouter configurée
- [x] Test rapide réussi

### **📈 Performance Attendue**
- **Setup** : < 5 minutes
- **Tests** : < 3 minutes
- **Analyses LLM** : 2-3 secondes
- **Applications web** : < 30 secondes de démarrage

### **🔍 Vérification Rapide**
```bash
# Vérification configuration
python -c "import os; print('API configurée:', 'OPENROUTER_API_KEY' in os.environ)"

# Test basic sans LLM
python -c "from argumentation_analysis.core import ArgumentationAnalyzer; print('Core OK')"

# Test avec LLM (si configuré)
python test_api_validation.py
```

---

## 🎓 **EXPLORATION RECOMMANDÉE**

### **🚀 Débutants (15 minutes)**
1. **Demo interactive** → `--interactive`
2. **Système web** → `start_webapp.py`
3. **Tests basiques** → `--quick-start`

### **🎯 Développeurs (1 heure)**
1. **Architecture** → Lire `docs/architecture/README.md`
2. **Tests avancés** → Exécuter suite complète
3. **Intégration LLM** → Tester chaque point d'entrée

### **🔬 Chercheurs (2 heures)**
1. **Code source** → Explorer modules core
2. **Validation complète** → Tous les tests
3. **Extension** → Patterns et architecture

---

## 📚 **DOCUMENTATION PRINCIPALE**

- **README.md** → Guide complet 381 lignes optimisées
- **docs/** → Documentation technique détaillée
- **Rapports de validation** → Résultats complets 5/5

---

## 🆘 **DÉPANNAGE RAPIDE**

### **Erreur : API Key manquante**
```bash
echo "OPENROUTER_API_KEY=sk-or-v1-votre-clé" > .env
```

### **Erreur : Java non trouvé**
```bash
# Installer Java 8+ ou définir JAVA_HOME
export JAVA_HOME=/path/to/java
```

### **Erreur : Dépendances manquantes**
```bash
pip install -r requirements.txt --force-reinstall
```

---

**🎯 Ce guide vous permet de démarrer et tester le projet en moins de 5 minutes !**

**📧 Support** : Consulter README.md ou documentation technique pour aide avancée