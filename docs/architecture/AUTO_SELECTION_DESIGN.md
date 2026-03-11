# Conception de l'Auto-Sélection de Pipeline

Ce document décrit l'architecture pour un mécanisme de sélection dynamique de pipeline d'analyse basé sur le contenu du texte d'entrée.

## 1. Vue d'ensemble et Objectifs

Actuellement, l'orchestrateur de traitement utilise une logique de fallback statique. L'objectif est de la remplacer par un "routeur" ou "sélecteur" intelligent qui choisit un pipeline d'analyse (simple, complexe, etc.) en fonction des caractéristiques du texte soumis.

Cela permettra :
-   D'économiser des ressources en utilisant des pipelines simples pour des textes courts ou simples.
-   D'appliquer des analyses plus profondes et coûteuses uniquement lorsque c'est nécessaire.
-   De rendre le système plus flexible et configurable.

## 2. Architecture Proposée

Le sélecteur sera implémenté comme une nouvelle méthode privée au sein de `AnalysisService`. Il sera appelé au début de la méthode `analyze_text`.

### Schéma de la cascade de décision

```mermaid
graph TD
    A[Requête /api/analyze] --> B{AnalysisService.analyze_text};
    B --> C{_select_pipeline(text)};
    C -- Texte court --> D[Pipeline: Simple];
    C -- Texte long --> E[Pipeline: Complexe];
    C -- Default --> F[Pipeline: Default];
    D --> G{Exécution: Analyse de structure simple};
    E --> H{Exécution: Analyse de structure + Sophismes complexes};
    F --> I{Exécution: Pipeline actuel};
    G --> J[Réponse];
    H --> J;
    I --> J;
```

### Composants

1.  **`PipelineSelector` (nouvelle classe ou méthode dans `AnalysisService`)**:
    *   Prend le texte en entrée.
    *   Analyse le texte selon des critères définis (longueur, etc.).
    *   Retourne un identifiant de pipeline (ex: `'simple'`, `'complex'`).

2.  **Stratégies de Pipeline (Pipelines)**:
    *   Chaque pipeline est une fonction ou une méthode qui orchestre une séquence spécifique d'opérations d'analyse (`_detect_fallacies_simple`, `_analyze_structure_regex`, `_detect_fallacies_agent`, etc.).

3.  **Configuration (`unified_config.py`)**:
    *   Un nouveau dictionnaire `pipeline_selection` sera ajouté pour définir les seuils et les pipelines associés.

## 3. Critères d'Analyse

Pour une première itération, le critère principal sera la **longueur du texte**.

-   **Pipeline "Simple"**: Pour les textes courts.
    -   **Seuil**: `len(text) < 500` caractères.
    -   **Actions**: Analyse de structure basée sur des expressions régulières, détection de sophismes simple basée sur des patrons.
-   **Pipeline "Complexe"**: Pour les textes longs ou nécessitant une analyse profonde.
    -   **Seuil**: `len(text) >= 500` caractères.
    -   **Actions**: Utilisation de l'agent `InformalAgent` pour une analyse sémantique, analyse de structure avancée, détection de sophismes contextuels.

## 4. Implémentation

### Modifications dans `AnalysisService`

```python
# argumentation_analysis/services/web_api/services/analysis_service.py

class AnalysisService:
    def __init__(self, config):
        """Initialise le service avec la configuration."""
        self.logger = logger
        self.config = config.get('analysis', {}) # Chargement de la config spécifique
        self.is_initialized = False
        self._initialize_components()

    def _select_pipeline(self, text: str) -> str:
        """Sélectionne le pipeline basé sur les critères configurés."""
        text_length = len(text)
        selection_rules = self.config.get('pipeline_selection', {}).get('rules', [])

        for rule in selection_rules:
            if rule['criteria']['type'] == 'length':
                if 'min' in rule['criteria'] and text_length < rule['criteria']['min']:
                    continue
                if 'max' in rule['criteria'] and text_length >= rule['criteria']['max']:
                    continue
                self.logger.info(f"Pipeline sélectionné: {rule['pipeline']} basé sur la longueur du texte ({text_length})")
                return rule['pipeline']

        default_pipeline = self.config.get('pipeline_selection', {}).get('default', 'complex')
        self.logger.info(f"Aucune règle ne correspond, utilisation du pipeline par défaut: {default_pipeline}")
        return default_pipeline

    async def analyze_text(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Orchestre l'analyse en utilisant le pipeline sélectionné.
        """
        start_time = time.time()
        
        pipeline_name = self._select_pipeline(request.text)
        
        if pipeline_name == 'simple':
            return await self._execute_simple_pipeline(request, start_time)
        elif pipeline_name == 'complex':
            return await self._execute_complex_pipeline(request, start_time)
        else:
            # Fallback vers le comportement actuel si le pipeline n'est pas reconnu
            self.logger.warning(f"Pipeline '{pipeline_name}' non reconnu. Utilisation du pipeline complexe par défaut.")
            return await self._execute_complex_pipeline(request, start_time)

    async def _execute_simple_pipeline(self, request: AnalysisRequest, start_time: float) -> AnalysisResponse:
        """Exécute une analyse rapide et légère."""
        self.logger.info("Exécution du pipeline SIMPLE")
        # Logique simplifiée ...
        fallacies = self._detect_fallacies_simple(request.text) # Nouvelle méthode simple
        structure = self._analyze_structure(request.text, request.options) # La méthode regex est déjà assez rapide
        # ... reste du calcul
        processing_time = time.time() - start_time
        return AnalysisResponse(...)

    async def _execute_complex_pipeline(self, request: AnalysisRequest, start_time: float) -> AnalysisResponse:
        """Exécute l'analyse complète existante."""
        self.logger.info("Exécution du pipeline COMPLEXE")
        # Logique actuelle ...
        fallacies = await self._detect_fallacies(request.text, request.options) # Comportement actuel
        structure = self._analyze_structure(request.text, request.options)
        # ... reste du calcul
        processing_time = time.time() - start_time
        return AnalysisResponse(...)

    def _detect_fallacies_simple(self, text: str) -> List[FallacyDetection]:
        """Détection de sophismes via le FallacyService basé sur les regex."""
        if self.fallacy_service:
            # ... appel au fallacy_service uniquement
            return [] 
        return []

```

### Modifications dans la configuration

Le fichier de configuration (`config/unified_config.py` ou un fichier YAML dédié comme `config/analysis_config.yml`) sera mis à jour pour inclure la logique de sélection.

```python
# Exemple dans config/unified_config.py ou un fichier chargé par celui-ci

def get_analysis_config():
    return {
        "pipeline_selection": {
            "default": "complex",
            "rules": [
                {
                    "pipeline": "simple",
                    "criteria": {
                        "type": "length",
                        "max": 500  # Textes de 0 à 499 caractères
                    }
                },
                {
                    "pipeline": "complex",
                    "criteria": {
                        "type": "length",
                        "min": 500 # Textes de 500 caractères et plus
                    }
                }
            ]
        },
        # ... autres configurations d'analyse
    }

```

## 5. Prochaines Étapes

1.  **Valider cette conception** avec l'équipe.
2.  **Implémenter les modifications** dans `AnalysisService`.
3.  **Refactoriser le chargement de la configuration** pour que `AnalysisService` ait accès à sa configuration.
4.  **Ajouter des tests unitaires** pour le `_select_pipeline` et des tests d'intégration pour les différents pipelines.