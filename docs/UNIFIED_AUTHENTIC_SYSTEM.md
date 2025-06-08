# Système Unifié Authentique - Documentation Technique

## Vue d'ensemble

Le **Système Unifié Authentique** est une refactorisation majeure du système d'analyse rhétorique qui introduit :

- ✅ **Configuration dynamique** permettant de choisir le type de logique (FOL/PL au lieu de Modal)
- ✅ **Sélection flexible des agents** et du type d'orchestration
- ✅ **Élimination complète des mocks** pour garantir l'authenticité 100%
- ✅ **Validation d'authenticité** des traces générées
- ✅ **Support PowerShell** standardisé

## Architecture du Système

### 1. Configuration Dynamique Unifiée

Le fichier [`config/unified_config.py`](../config/unified_config.py) centralise tous les paramètres configurables :

```python
from config.unified_config import UnifiedConfig, LogicType, MockLevel

# Configuration authentique FOL
config = UnifiedConfig(
    logic_type=LogicType.FOL,                    # FOL au lieu de Modal
    agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
    orchestration_type=OrchestrationType.UNIFIED,
    mock_level=MockLevel.NONE,                   # Aucun mock
    taxonomy_size=TaxonomySize.FULL,             # 1000 nœuds
    require_real_gpt=True,                       # GPT-4o-mini authentique
    require_real_tweety=True,                    # Tweety JAR réel
    require_full_taxonomy=True                   # Taxonomie complète
)
```

### 2. Agent FOL/PL de Substitution

Le nouvel agent [`FOLLogicAgent`](../argumentation_analysis/agents/core/logic/fol_logic_agent.py) remplace l'agent Modal défaillant :

```python
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent

# Création de l'agent FOL
agent = FOLLogicAgent(agent_name="AuthenticFOLAgent")
await agent.setup_agent_components()

# Analyse avec logique FOL
result = await agent.analyze("Tous les hommes sont mortels. Socrate est un homme.")
print(f"Formules FOL: {result.formulas}")
print(f"Cohérence: {result.consistency_check}")
```

### 3. Élimination Automatique des Mocks

Le système de détection [`mock_elimination.py`](../scripts/validation/mock_elimination.py) identifie et élimine tous les mocks :

```python
from scripts.validation.mock_elimination import MockDetector

detector = MockDetector(".")
report = detector.scan_project()
print(f"Score d'authenticité: {report.authenticity_score:.1%}")
```

## Guide d'Utilisation

### Commande PowerShell Standardisée

La commande PowerShell standardisée pour une authenticité 100% :

```powershell
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m scripts.main.analyze_text --source-type simple --logic-type fol --agents informal,fol_logic,synthesis --orchestration unified --mock-level none --taxonomy full --format markdown --verbose"
```

### Paramètres de Configuration

| Paramètre | Valeurs | Description | Défaut |
|-----------|---------|-------------|---------|
| `--logic-type` | `fol`, `pl`, `modal` | Type de logique formelle | `fol` |
| `--agents` | `informal,fol_logic,synthesis,extract,pm` | Agents à utiliser | `informal,fol_logic,synthesis` |
| `--orchestration` | `unified`, `conversation`, `custom` | Type d'orchestration | `unified` |
| `--mock-level` | `none`, `partial`, `full` | Niveau de mocking | `none` |
| `--taxonomy` | `full`, `mock` | Taille de taxonomie | `full` |
| `--require-real-gpt` | - | Force GPT-4o-mini réel | `True` |
| `--require-real-tweety` | - | Force Tweety JAR authentique | `True` |
| `--require-full-taxonomy` | - | Force taxonomie 1000 nœuds | `True` |

### Configurations Prédéfinies

#### Configuration Authentique FOL
```python
config = PresetConfigs.authentic_fol()
# Logic: FOL, Agents: [informal, fol_logic, synthesis], Mock: none
```

#### Configuration Authentique PL
```python
config = PresetConfigs.authentic_pl()
# Logic: PL, Agents: [informal, fol_logic, synthesis], Mock: none
```

#### Configuration Développement
```python
config = PresetConfigs.development()
# Logic: FOL, Mock: partial, Taxonomy: mock
```

## Tests et Validation

### 1. Tests de Validation Complète

```powershell
# Test complet du système unifié
python -m scripts.test.test_unified_authentic_system
```

### 2. Audit d'Authenticité

```powershell
# Génération du rapport d'authenticité
python -m scripts.validation.mock_elimination
```

### 3. Démonstration PowerShell

```powershell
# Démonstration avec tests et validation
.\scripts\demo\demo_unified_authentic_system.ps1 -RunTests -AuthenticityReport -Verbose
```

## Validation d'Authenticité

### Critères d'Authenticité 100%

1. **✅ Services LLM Authentiques**
   - Utilisation exclusive de GPT-4o-mini via API OpenAI
   - Aucun service LLM simulé
   - Validation des clés API et connexions

2. **✅ TweetyProject Authentique**
   - Utilisation du JAR Tweety complet
   - JVM initialisée avec classpath réel
   - Aucune simulation de solveur logique

3. **✅ Taxonomie Complète**
   - Chargement de la taxonomie 1000 nœuds
   - Aucune taxonomie réduite ou simulée
   - Validation du nombre de nœuds

4. **✅ Tool Calls Authentiques**
   - Tous les appels d'outils sont réels
   - Aucune simulation de réponse
   - Traçabilité complète des interactions

### Score d'Authenticité

Le score d'authenticité est calculé selon :

```
Score = 1.0 - (Mocks_Critiques × 10 + Mocks_Haute × 5 + Mocks_Moyenne × 2) / 100
```

**Objectif : Score ≥ 80% pour validation**

## Avantages du Système Unifié

### 1. Fiabilité Améliorée
- **Logique FOL/PL** : Alternative stable à Modal Logic
- **Agents authentiques** : Élimination des défaillances de mocks
- **Traces vérifiables** : Validation end-to-end possible

### 2. Flexibilité de Configuration
- **Paramètres dynamiques** : Modification sans changement de code
- **Profiles prédéfinis** : Configurations pour dev/prod/test
- **Validation automatique** : Détection d'incohérences

### 3. Transparence Complète
- **Aucun mock caché** : Visibilité totale des composants
- **Traçabilité authentique** : Chaque interaction documentée
- **Validation continue** : Monitoring de l'authenticité

## Résolution de Problèmes

### Problème : Agent Modal Logic échoue
**Solution** : Utiliser `--logic-type fol` ou `--logic-type pl`

### Problème : Mocks détectés malgré `--mock-level none`
**Solution** : Exécuter l'audit d'authenticité et éliminer les mocks critiques

### Problème : Échec de connexion LLM
**Solution** : Vérifier les variables d'environnement `OPENAI_API_KEY` et `OPENAI_ORG_ID`

### Problème : JVM Tweety non démarrée
**Solution** : Vérifier la présence du JAR dans `libs/` et les permissions

### Problème : Taxonomie trop petite
**Solution** : Utiliser `--taxonomy full` et vérifier le fichier de taxonomie

## Roadmap Future

### Version 2.1 (Prochaine)
- Support pour logique temporelle
- Intégration avec base de données vectorielle
- API REST pour intégration externe

### Version 2.2 (Future)
- Interface web pour configuration
- Métriques temps réel d'authenticité
- Export vers formats standards (OWL, RDF)

## Références Techniques

### Structure du Projet
```
project/
├── config/
│   ├── unified_config.py          # Configuration dynamique
│   └── orchestration_config.yaml  # Configuration legacy
├── argumentation_analysis/
│   └── agents/core/logic/
│       └── fol_logic_agent.py     # Agent FOL/PL
├── scripts/
│   ├── main/
│   │   └── analyze_text.py        # Script principal modifié
│   ├── validation/
│   │   └── mock_elimination.py    # Élimination mocks
│   ├── test/
│   │   └── test_unified_authentic_system.py  # Tests
│   └── demo/
│       └── demo_unified_authentic_system.ps1  # Démo PowerShell
└── docs/
    └── UNIFIED_AUTHENTIC_SYSTEM.md  # Cette documentation
```

### APIs Principales

#### UnifiedConfig
```python
class UnifiedConfig:
    logic_type: LogicType              # Type de logique
    agents: List[AgentType]            # Agents sélectionnés
    orchestration_type: OrchestrationType  # Type d'orchestration
    mock_level: MockLevel              # Niveau de mocking
    taxonomy_size: TaxonomySize        # Taille taxonomie
    require_real_gpt: bool             # Force LLM authentique
    require_real_tweety: bool          # Force Tweety authentique
    require_full_taxonomy: bool        # Force taxonomie complète
```

#### FOLLogicAgent
```python
class FOLLogicAgent(BaseLogicAgent):
    async def analyze(text: str) -> FOLAnalysisResult
    async def setup_agent_components() -> bool
    def get_analysis_summary() -> Dict[str, Any]
```

#### MockDetector
```python
class MockDetector:
    def scan_project() -> AuthenticityReport
    def _categorize_mocks() -> None
    def _calculate_authenticity_score() -> float
```

## Support et Contact

Pour toute question technique sur le système unifié authentique :

1. **Documentation** : Consulter cette documentation complète
2. **Tests** : Exécuter les scripts de validation
3. **Debugging** : Utiliser les modes verbeux et les rapports d'authenticité
4. **Issues** : Documenter les problèmes avec traces complètes

---

**Dernière mise à jour** : 7 janvier 2025  
**Version du système** : 2.0.0 - Unified Authentic  
**Statut** : Production Ready avec Authenticité 100%