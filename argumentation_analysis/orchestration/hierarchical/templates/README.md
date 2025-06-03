# Templates d'architecture hiérarchique

## Utilisation des templates

Chaque template fournit une structure de base pour intégrer de nouveaux composants au système d'orchestration. Les fichiers sont organisés par type de composant.

### 1. Agent Template
**Fichier**: `agent_template.py`

**Structure**:
- Classe `BaseAgent` avec méthodes à implémenter
- Configuration d'exemple (`AGENT_CONFIG_EXAMPLE`)

**Étapes d'implémentation**:
1. Créer une sous-classe de `BaseAgent`
2. Implémenter la méthode `process()`
3. Définir les dépendances et capacités dans la configuration
4. Intégrer dans l'orchestrateur via `register_agent()`

### 2. Outil d'Analyse Template
**Fichier**: `analysis_tool_template.py`

**Structure**:
- Classe `BaseAnalysisTool` avec méthodes d'analyse
- Configuration d'exemple (`ANALYSIS_TOOL_CONFIG_EXAMPLE`)

**Étapes d'implémentation**:
1. Créer une sous-classe de `BaseAnalysisTool`
2. Implémenter la méthode `analyze()`
3. Définir les formats d'entrée/sortie
4. Intégrer dans l'orchestrateur via `register_analysis_tool()`

### 3. Stratégie d'Orchestration Template
**Fichier**: `strategy_template.py`

**Structure**:
- Classe `BaseOrchestrationStrategy` avec gestion de priorité
**Étapes d'implémentation**:
1. Créer une sous-classe de `BaseOrchestrationStrategy`
2. Implémenter `plan_execution()` et `allocate_resources()`
3. Définir les règles de priorité dans la configuration
4. Intégrer dans l'orchestrateur via `register_strategy()`

### 4. Type d'Analyse Template
**Fichier**: `analysis_type_template.py`

**Structure**:
- Classe `BaseAnalysisType` avec validation de configuration

**Étapes d'implémentation**:
1. Créer une sous-classe de `BaseAnalysisType`
2. Implémenter la méthode `analyze()`
3. Définir les paramètres et dépendances dans la configuration
4. Intégrer dans l'orchestrateur via `register_analysis_type()`

## Guide général d'utilisation

1. **Choisir le type de template** correspondant à votre besoin
2. **Créer une nouvelle classe** en héritant de la classe de base
3. **Implémenter les méthodes abstraites** avec la logique spécifique
4. **Définir la configuration** avec les paramètres requis
5. **Enregistrer le composant** dans l'orchestrateur principal
6. **Ajouter des tests** dans le répertoire `tests/` correspondant

Les templates respectent l'architecture en trois niveaux (stratégique, tactique, opérationnel) et utilisent les conventions de nommage du projet. Les commentaires dans chaque template détaillent les points d'extension possibles.