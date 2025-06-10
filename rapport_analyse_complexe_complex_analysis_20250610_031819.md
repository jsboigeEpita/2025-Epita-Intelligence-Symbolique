# 📊 Rapport d'Analyse Complexe Multi-Agents

**Session ID:** `complex_analysis_20250610_031819`  
**Date:** 10/06/2025 à 03:18:19  
**Durée totale:** 36.98 secondes  

## 📝 Source Analysée

**Titre:** Discours Politique Test - Réforme Éducative  
**Longueur:** 585 caractères  
**Type:** Texte politique simulé  

### Extrait du texte
```

        Le gouvernement français doit absolument réformer le système éducatif. 
        Tous les pédagogues reconnus s'accordent à dire que notre méthode est révolutionnaire.
        Si nous n'agissons pas immédiatement, c'est l'échec scolaire garanti pour toute une génération.
        Les partis d'opposition ne proposent que des mesures dépassées qui ont échoué en Finlande.
        Cette réforme permettra de créer des millions d'emplois et de sauver notre économie.
        Les parents responsa
```

## 🤖 Agents Orchestrés

4 agents ont participé à l'analyse :
- **CorpusManager** (1 interactions)
- **InformalAnalysisAgent** (1 interactions)
- **RhetoricalAnalysisAgent** (1 interactions)
- **SynthesisAgent** (1 interactions)

## 🔧 Outils Utilisés

4 types d'outils ont été appelés :
- **load_random_extract** (1 appels)
- **analyze_fallacies** (1 appels)
- **analyze_rhetoric** (1 appels)
- **cross_validate_analysis** (1 appels)

## 📖 Trace Conversationnelle Détaillée

### 🔄 Interaction 1: CorpusManager → load_random_extract

**⏱️ Timestamp:** `2025-06-10T03:18:19.475799`  
**⚡ Durée:** 0.00s  

**📥 Entrée (34 caractères):**
```
Sélection aléatoire corpus chiffré
```

**📤 Sortie (64 caractères):**
```
Extrait: Discours Politique Test - Réforme Éducative (585 chars)
```

---

### 🔄 Interaction 2: InformalAnalysisAgent → analyze_fallacies

**⏱️ Timestamp:** `2025-06-10T03:18:56.448689`  
**⚡ Durée:** 36.97s  

**📥 Entrée (585 caractères):**
```

        Le gouvernement français doit absolument réformer le système éducatif. 
        Tous les pédagogues reconnus s'accordent à dire que notre méthode est révolutionnaire.
        Si nous n'agisso...
```

**📤 Sortie (7607 caractères):**
```
{'fallacies': {'mode': 'fallacies', 'result': {'fallacies': [{'nom': "Appel à l'autorité", 'explication': "L'argument repose sur le fait que tous les pédagogues reconnus soutiennent la réforme sans fournir de preuves ou de données spécifiques, ce qui ne garantit pas la véracité de l'affirmation.", '...
```

---

### 🔄 Interaction 3: RhetoricalAnalysisAgent → analyze_rhetoric

**⏱️ Timestamp:** `2025-06-10T03:18:56.450155`  
**⚡ Durée:** 3.50s  

**📥 Entrée (585 caractères):**
```

        Le gouvernement français doit absolument réformer le système éducatif. 
        Tous les pédagogues reconnus s'accordent à dire que notre méthode est révolutionnaire.
        Si nous n'agisso...
```

**📤 Sortie (248 caractères):**
```
{'rhetorical_devices': ['métaphore', 'anaphore', "appel à l'autorité"], 'persuasion_score': 0.75, 'emotional_appeals': ['peur', 'espoir', 'responsabilité'], 'target_audience': 'parents et éducateurs', 'authentic': True, 'model_used': 'gpt-4o-mini'}
```

---

### 🔄 Interaction 4: SynthesisAgent → cross_validate_analysis

**⏱️ Timestamp:** `2025-06-10T03:18:56.451294`  
**⚡ Durée:** 2.80s  

**📥 Entrée (7878 caractères):**
```
Fallacies: {'fallacies': {'mode': 'fallacies', 'result': {'fallacies': [{'nom': "Appel à l'autorité", 'explication': "L'argument repose sur le fait que tous les pédagogues reconnus soutiennent la réfo...
```

**📤 Sortie (323 caractères):**
```
{'coherence_score': 0.68, 'argument_structure': 'faible - nombreux sophismes', 'credibility_assessment': 'discours politique typique', 'cross_validation': 'cohérence entre analyses fallacies et rhétorique', 'recommendations': ['vérifier les sources', 'demander des preuves'], 'authentic': True, 'mode...
```

---

## 🎯 Résultats Finaux

### Mode Fallacies
**Aucun sophisme détecté**

**Authenticité:** ✅ Analyse LLM authentique  
**Modèle:** gpt-4o-mini  
**Confiance:** 0.00  

## 📈 Métriques de Performance

- **Interactions totales:** 4
- **Agents utilisés:** 4
- **Outils appelés:** 4
- **Durée moyenne par interaction:** 9.24s
- **Taux de succès:** 100.00%

## 🔍 Analyse des Patterns

### Répartition par Agent
- **CorpusManager:** 1 interactions, 0.00s total
- **InformalAnalysisAgent:** 1 interactions, 36.97s total
- **RhetoricalAnalysisAgent:** 1 interactions, 3.50s total
- **SynthesisAgent:** 1 interactions, 2.80s total

### Répartition par Outil
- **load_random_extract:** 1 appels, 0.00s total
- **analyze_fallacies:** 1 appels, 36.97s total
- **analyze_rhetoric:** 1 appels, 3.50s total
- **cross_validate_analysis:** 1 appels, 2.80s total

---

*Rapport généré automatiquement par l'Orchestrateur d'Analyse Complexe*  
*Session: complex_analysis_20250610_031819*
