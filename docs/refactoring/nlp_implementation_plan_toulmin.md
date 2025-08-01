# Plan d'Implémentation NLP pour le Modèle de Toulmin (v2 - Self-Hosted)

**Date :** 1er Août 2025
**Auteur :** Roo, Architecte IA
**Statut :** Approuvé pour implémentation

## 1. Stratégie Choisie : Modèle Qwen3-1.7B quantisé, servi par vLLM

Après analyse et sur la base des nouvelles directives, la stratégie retenue est l'utilisation d'un **modèle de langage local, servi par une infrastructure haute-performance.**

*   **Modèle :** `unsloth/Qwen3-1.7B-Base-unsloth-bnb-4bit`. Il s'agit d'un modèle de la famille Qwen3, performant et multilingue, optimisé par Unsloth via une quantification 4-bit pour un excellent rapport performance/consommation de VRAM.
*   **Serveur d'inférence :** `vLLM`. Il sera utilisé pour servir le modèle via une API compatible OpenAI. `vLLM` est choisi pour son excellente performance (throughput et latence) grâce à des optimisations comme PagedAttention.
*   **Approche d'extraction :** "Zero-shot prompting" avec une sortie JSON structurée. Nous tirerons parti du mode "thinking" de Qwen3 pour améliorer la qualité de l'extraction des composants de Toulmin.

### Justification du Choix

*   **Maîtrise et Confidentialité :** L'hébergement local garantit une confidentialité totale des données analysées et un contrôle complet sur l'infrastructure.
*   **Performance :** `vLLM` est une solution de pointe pour servir des LLMs, assurant une latence faible et un débit élevé, ce qui est crucial pour une intégration réactive dans nos outils.
*   **Optimisation des coûts :** L'utilisation d'un modèle open-source et quantisé supprime les coûts récurrents liés aux APIs cloud et permet un déploiement sur du matériel grand public (ex: GPU avec >4GB de VRAM).
*   **Évolutivité vers le Fine-tuning :** Le choix d'un modèle optimisé par `unsloth` ouvre la porte à de futures campagnes de fine-tuning (via QLoRA) pour spécialiser le modèle sur notre tâche d'analyse argumentative, en bénéficiant de l'écosystème Unsloth (2x plus rapide, 70% de VRAM en moins).

## 2. Architecture de Déploiement

L'architecture sera composée de deux services distincts :
1.  **Le Serveur LLM (`vLLM`) :** Un processus dédié qui charge le modèle `Qwen3` en mémoire et expose une API REST compatible OpenAI sur le réseau local (ex: `http://localhost:8000`).
2.  **L'Application Cliente (`SemanticArgumentAnalyzer`) :** Notre code Python qui, au lieu d'intégrer un modèle directement, agira comme un client HTTP vers le serveur `vLLM`.

![Architecture Diagram](httpsa://i.imgur.com/your-diagram-image.png "Cette approche découple le modèle de l'application, facilitant la mise à l'échelle et la maintenance.")

## 3. Dépendances Requises

*   **Pour le serveur d'inférence (`vLLM`) :**
    *   `vllm>=0.8.5`: La bibliothèque de serving.
    *   `huggingface_hub`, `hf_transfer`: Pour télécharger les modèles depuis le Hub.
    *   Un environnement avec Python 3.10+ et les pilotes CUDA correspondants.
*   **Pour l'application cliente (`SemanticArgumentAnalyzer`) :**
    *   `openai`: Le SDK sera utilisé pour communiquer avec l'API compatible OpenAI de `vLLM`.
    *   `pydantic`: Pour la validation de la réponse JSON.

Ces dépendances devront être gérées dans leurs environnements respectifs.

## 4. Plan d'Implémentation Détaillé

### Étape 1 : Mise en place du Serveur vLLM

1.  **Préparation de l'environnement :** Créer un environnement virtuel dédié pour le serveur et installer les dépendances :
    ```bash
    pip install "vllm>=0.8.5" huggingface_hub hf_transfer
    ```
2.  **Lancement du serveur :** Créer un script de lancement (ex: `run_vllm_server.sh`) pour démarrer le serveur `vLLM` avec le bon modèle et les bonnes optimisations.
    ```bash
    #!/bin/bash
    
    # Exporter la variable pour utiliser ModelScope si nécessaire, sinon HF est par défaut
    # export VLLM_USE_MODELSCOPE=true
    
    # Lancer le serveur vLLM
    vllm serve unsloth/Qwen3-1.7B-Base-unsloth-bnb-4bit \
        --model-name Qwen3-1.7B-Toulmin-Analyzer \
        --host 0.0.0.0 \
        --port 8000 \
        --enable-reasoning \
        --reasoning-parser qwen3
    ```
    *   `--model-name` permet de donner un alias au modèle pour les appels API.
    *   `--enable-reasoning` et `--reasoning-parser qwen3` sont cruciaux pour exploiter et parser correctement le mode "thinking" du modèle.

### Étape 2 : Considérations sur le Modèle et le Prompt

#### 2.1. Confiance dans les Capacités de Qwen3-1.7B
Des tests préliminaires (documentés séparément) ont montré que le modèle `Qwen3-1.7B` est capable d'identifier les composants du modèle de Toulmin dans un texte en anglais en mode *zero-shot*, sans nécessiter de fine-tuning initial. La conversation de test a révélé que le modèle, bien que n'utilisant pas toujours la terminologie exacte des 6 composants canoniques, comprend parfaitement le concept et le cadre d'analyse argumentative.

La fonctionnalité clé ici est le mode **"thinking"** (ou raisonnement interne) du modèle. Ce mode permet au LLM de "réfléchir" aux étapes de l'analyse avant de produire la réponse finale. Cette capacité est essentielle pour des tâches complexes comme la décomposition argumentative.

#### 2.2. Modulation du mode "Thinking" pour la Performance
Le mode "thinking" de Qwen3, activé via le flag `--enable-reasoning` de `vLLM`, n'est pas monolithique. Il sera possible de le moduler pour ajuster le compromis entre vitesse et précision :
*   **Vitesse accrue :** En analysant les logits des tokens de fin de raisonnement, on peut encourager le modèle à conclure son analyse plus rapidement. Utile pour des analyses en temps réel où une latence faible est critique.
*   **Précision accrue :** Inversement, en décourageant la sortie précoce, on peut allouer plus de "temps de calcul" au modèle pour des analyses plus profondes, au détriment de la vitesse.

Cette modularité sera un axe d'optimisation important après la mise en place de la solution de base.

### Étape 3 : Adaptation de la logique Cliente (`SemanticArgumentAnalyzer`)

La classe sera réécrite pour utiliser un client OpenAI pointant vers notre serveur local.

1.  **Mise à jour du `__init__` :**
    ```python
    from openai import OpenAI
    
    class SemanticArgumentAnalyzer:
        def __init__(self, api_base_url="http://localhost:8000/v1", model_name="Qwen3-1.7B-Toulmin-Analyzer"):
            self.client = OpenAI(
                base_url=api_base_url,
                api_key="EMPTY"  # vLLM n'exige pas de clé par défaut
            )
            self.model_name = model_name
            self.system_prompt_template = """...""" # Le prompt défini ci-dessous
    ```

2.  **Conception du Prompt pour Qwen3 :**
    Le prompt doit utiliser le template de chat de Qwen3 (`<|im_start|>...`) et l'instruire pour utiliser son mode de pensée et formater la sortie en JSON.

    ```text
    <|im_start|>system
    Vous êtes un expert en rhétorique spécialisé dans le modèle de Toulmin. Votre tâche est d'analyser le texte de l'utilisateur et de le décomposer en ses composantes structurelles. 
    Utilisez votre capacité de raisonnement interne pour construire la meilleure analyse possible.
    Retournez votre analyse exclusivement au format JSON. Ne fournissez aucune explication en dehors de l'objet JSON.
    La structure attendue est la suivante :
    {
      "claim": {"text": "...", "confidence_score": ...},
      "data": [{"text": "...", "confidence_score": ...}],
      "warrant": {"text": "...", "confidence_score": ...},
      "backing": {"text": "...", "confidence_score": ...},
      "qualifier": {"text": "...", "confidence_score": ...},
      "rebuttal": {"text": "...", "confidence_score": ...}
    }
    <|im_end|>
    <|im_start|>user
    {argument_text}
    <|im_end|>
    <|im_start|>assistant
    ```

3.  **Réécriture de la méthode `analyze` :**
    ```python
    import json
    from pydantic import ValidationError
    from argumentation_analysis.core.models.toulmin_model import ToulminAnalysisResult
    
    def analyze(self, argument_text: str) -> ToulminAnalysisResult:
        # Le prompt est directement le message utilisateur, le système prompt est géré par le template
        messages = [
            # Note: le prompt système est généralement géré par le template de vLLM,
            # mais on peut le spécifier ici si nécessaire.
            # Pour Qwen3, le template suffit souvent.
            {"role": "user", "content": argument_text}
        ]
        
        try:
            chat_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.6,  # Recommandé pour le "thinking mode"
                top_p=0.95,
                max_tokens=4096,
                response_format={"type": "json_object"} # Demander une sortie JSON si supporté
            )
            
            response_content = chat_response.choices[0].message.content
            
            # Valider avec Pydantic
            analysis_result = ToulminAnalysisResult.model_validate_json(response_content)
            return analysis_result

        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Erreur de parsing de la réponse LLM : {e}")
            return ToulminAnalysisResult(claim=None, data=[])
        except Exception as e:
            print(f"Erreur lors de l'appel au LLM via vLLM : {e}")
            return ToulminAnalysisResult(claim=None, data=[])
    ```
    *Note: L'option `response_format={"type": "json_object"}` est une fonctionnalité standard pour forcer le JSON, compatible avec vLLM.*

### Étape 4 : Intégration avec l'Écosystème Existant (`Semantic Kernel`)

L'un des avantages stratégiques majeurs de l'utilisation de `vLLM` est qu'il expose une **API compatible avec OpenAI**.

*   **Cohérence du Projet :** L'analyse de la codebase a révélé une utilisation extensive de `semantic-kernel` avec le connecteur `OpenAIChatCompletion`. Cela signifie que l'écosystème d'orchestration est déjà en place.
*   **Intégration Transparente :** Le `SemanticArgumentAnalyzer`, ou tout autre agent utilisant `semantic-kernel`, n'aura pas besoin de code spécifique pour `vLLM`. Il suffira de configurer le `Kernel` pour qu'il pointe vers l'endpoint local du serveur `vLLM` au lieu de l'URL de l'API OpenAI.

    ```python
    # Exemple de configuration du kernel pour utiliser le service local
    import semantic_kernel as sk
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    kernel = sk.Kernel()

    # Au lieu de configurer avec une clé API OpenAI, on configure avec l'URL de base de vLLM
    kernel.add_chat_service(
        "Qwen3-local",
        OpenAIChatCompletion(
            ai_model_id="Qwen3-1.7B-Toulmin-Analyzer", # L'alias défini dans la commande vLLM
            base_url="http://localhost:8000/v1",
            api_key="EMPTY" # vLLM n'a pas besoin de clé par défaut
        )
    )
    ```
Cette approche garantit que les nouveaux outils s'intègrent de manière fluide et cohérente avec les patterns d'architecture déjà établis dans le projet, minimisant ainsi la friction et la courbe d'apprentissage.

## 5. Stratégie de Test Mise à Jour

1.  **Tests Unitaires du `SemanticArgumentAnalyzer` :**
    *   **Utiliser un Mock de `openai.Client` :** Les tests doivent mocker l'instance du client pour simuler les réponses du serveur vLLM sans requérir de connexion réseau.
    *   **Scénarios de test :**
        *   Réponse JSON valide et conforme.
        *   Réponse JSON valide mais structurellement incorrecte (test de la validation Pydantic).
        *   Réponse non-JSON (test de la gestion d'erreur `JSONDecodeError`).
        *   Erreur de l'API (ex: `APIConnectionError`).
2.  **Tests d'Intégration :**
    *   Un script de test d'intégration sera créé (ex: dans `tests/integration/`).
    *   Ce script devra :
        1.  Lancer le serveur `vLLM` en sous-processus.
        2.  Attendre que le serveur soit prêt.
        3.  Instancier le `SemanticArgumentAnalyzer` pointant vers le serveur de test.
        4.  Exécuter un test d'analyse sur un exemple de texte.
        5.  Arrêter le serveur `vLLM`.
    *   Cela valide la chaîne complète : `Client -> Serveur vLLM -> Modèle Qwen3`.

Ce plan actualisé fournit une feuille de route précise pour une implémentation robuste, performante et souveraine de notre capacité d'analyse sémantique.
