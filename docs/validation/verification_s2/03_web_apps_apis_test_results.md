# Rapport de Preuves de Test : Web-Apps et APIs

Ce document contient les résultats détaillés de la campagne de test exhaustive menée le 2025-06-25 03:04:51.

## 1. API FastAPI (`api/main.py`)

### **Nom :** `FastAPI - GET /api/health`
- **Commande de Test :** `requests.get('http://127.0.0.1:8095/api/health')`
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "status": "operational",
  "service_status": {
    "details": "API is healthy and running."
  }
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `FastAPI - GET /api/status`
- **Commande de Test :** `requests.get('http://127.0.0.1:8095/api/status')`
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "status": "operational",
  "service_status": {
    "service_type": "OrchestrationServiceManager",
    "gpt4o_mini_enabled": true,
    "mock_disabled": true,
    "manager_initialized": true,
    "uptime_seconds": 0.912453
  }
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `FastAPI - GET /api/examples`
- **Commande de Test :** `requests.get('http://127.0.0.1:8095/api/examples')`
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "examples": [
    {
      "title": "Logique Propositionnelle",
      "text": "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.",
      "type": "propositional"
    },
    {
      "title": "Logique Modale",
      "text": "Il est nécessaire que tous les hommes soient mortels. Socrate est un homme. Il est donc nécessaire que Socrate soit mortel.",
      "type": "modal"
    },
    {
      "title": "Argumentation Complexe",
      "text": "L'intelligence artificielle représente à la fois une opportunité et un défi. D'un côté, elle peut révolutionner la médecine et l'éducation. De l'autre, elle pose des questions éthiques fondamentales sur l'emploi et la vie privée.",
      "type": "comprehensive"
    },
    {
      "title": "Paradoxe Logique",
      "text": "Cette phrase est fausse. Si elle est vraie, alors elle est fausse. Si elle est fausse, alors elle est vraie.",
      "type": "paradox"
    }
  ]
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `FastAPI - GET /api/endpoints`
- **Commande de Test :** `requests.get('http://127.0.0.1:8095/api/endpoints')`
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "endpoints": [
    {
      "path": "/api/analyze",
      "methods": [
        "POST"
      ],
      "description": "Analyze Text Endpoint"
    },
    {
      "path": "/api/status",
      "methods": [
        "GET"
      ],
      "description": "Status Endpoint"
    },
    {
      "path": "/api/examples",
      "methods": [
        "GET"
      ],
      "description": "Get Examples Endpoint"
    },
    {
      "path": "/api/health",
      "methods": [
        "GET"
      ],
      "description": "Health Check Endpoint"
    },
    {
      "path": "/api/endpoints",
      "methods": [
        "GET"
      ],
      "description": "List Endpoints Endpoint"
    },
    {
      "path": "/api/v1/framework/analyze",
      "methods": [
        "POST"
      ],
      "description": "Analyze Framework Endpoint"
    },
    {
      "path": "/",
      "methods": [
        "GET"
      ],
      "description": "Root"
    }
  ]
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `FastAPI - POST /api/analyze`
- **Commande de Test :** `requests.post('http://127.0.0.1:8095/api/analyze', json=...)`
- **Payload :**
  ```json
{
  "text": "Socrates is a man, all men are mortal, therefore Socrates is mortal."
}
  ```
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "analysis_id": "c8dd9148",
  "status": "success",
  "results": {
    "overall_quality": 0.0,
    "fallacy_count": 0,
    "fallacies": [],
    "argument_structure": {
      "arguments": []
    },
    "suggestions": [
      "Analyser chaque argument individuellement."
    ],
    "summary": "0 arguments extraits avec succès.",
    "metadata": {
      "duration": 0.042594194412231445,
      "service_status": "active",
      "components_used": [
        "TweetyArgumentReconstructor_centralized"
      ]
    }
  }
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `FastAPI - POST /api/v1/framework/analyze`
- **Commande de Test :** `requests.post('http://127.0.0.1:8095/api/v1/framework/analyze', json=...)`
- **Payload :**
  ```json
{
  "arguments": [
    "a",
    "b",
    "c"
  ],
  "attacks": [
    [
      "a",
      "b"
    ],
    [
      "b",
      "c"
    ]
  ]
}
  ```
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "analysis": {
    "extensions": null,
    "argument_status": {},
    "graph_properties": {
      "num_arguments": 3,
      "num_attacks": 2,
      "has_cycles": false,
      "cycles": [],
      "self_attacking_nodes": []
    }
  }
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

## 2. Application Web Flask (`argumentation_analysis/services/web_api/app.py`)

### **Nom :** `Flask - GET /api/health (deep check)`
- **Commande de Test :** `requests.get('http://127.0.0.1:8095/api/health')`
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "message": "Server is up and responding.",
  "status": "ok"
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `Flask - GET /api/endpoints`
- **Commande de Test :** `requests.get('http://127.0.0.1:8095/api/endpoints')`
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "api_name": "API d'Analyse Argumentative",
  "endpoints": {
    "GET /api/health": {
      "description": "Vérification de l'état de l'API"
    },
    "POST /api/analyze": {
      "description": "Analyse complète d'un texte argumentatif"
    },
    "POST /api/fallacies": {
      "description": "Détection de sophismes"
    },
    "POST /api/framework": {
      "description": "Construction d'un framework de Dung"
    },
    "POST /api/validate": {
      "description": "Validation logique d'un argument"
    }
  },
  "version": "1.0.0"
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `Flask - POST /api/analyze`
- **Commande de Test :** `requests.post('http://127.0.0.1:8095/api/analyze', json=...)`
- **Payload :**
  ```json
{
  "text": "Cats are better than dogs because they are more independent."
}
  ```
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "analysis_options": {
    "analyze_structure": true,
    "detect_fallacies": true,
    "evaluate_coherence": true,
    "include_context": true,
    "severity_threshold": 0.5
  },
  "analysis_timestamp": "Wed, 25 Jun 2025 03:05:22 GMT",
  "argument_structure": {
    "argument_type": "assertion",
    "coherence": 0.175,
    "conclusion": "Cats are better than dogs because they are more independent",
    "premises": [],
    "strength": 0.24
  },
  "coherence_score": 0.175,
  "fallacies": [
    {
      "confidence": 0.99,
      "context": "Cats are better than dogs because they are more independent.",
      "description": "This is a mock response to test the application flow without a real LLM call.",
      "explanation": "Mocked during integration test.",
      "location": {},
      "name": "Mock Fallacy",
      "severity": 0.5,
      "type": "semantic"
    }
  ],
  "fallacy_count": 1,
  "overall_quality": 0.6319999999999999,
  "processing_time": 0.006514549255371094,
  "success": tru
... (tronqué)

    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `Flask - POST /api/validate`
- **Commande de Test :** `requests.post('http://127.0.0.1:8095/api/validate', json=...)`
- **Payload :**
  ```json
{
  "premises": [
    "p -> q",
    "p"
  ],
  "conclusion": "q"
}
  ```
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "argument_type": "deductive",
  "conclusion": "q",
  "premises": [
    "p -> q",
    "p"
  ],
  "processing_time": 0.0005335807800292969,
  "result": {
    "conclusion_analysis": {
      "clarity_score": 0.3,
      "follows_logically": 0.5,
      "is_supported": 0.5,
      "length": 1,
      "specificity_score": 0.7,
      "strength": 0.5,
      "text": "q",
      "word_count": 1
    },
    "is_valid": false,
    "issues": [
      "1 prémisse(s) manque(nt) de clarté. Reformulez-les pour les rendre plus explicites.",
      "La conclusion manque de clarté. Reformulez-la pour la rendre plus explicite.",
      "Les prémisses ne sont pas suffisamment pertinentes pour la conclusion. Assurez-vous que vos prémisses soutiennent directement votre conclusion.",
      "L'argument est incomplet. Ajoutez des prémisses intermédiaires pour renforcer le lien entre vos prémisses et votre conclusion.",
      "Écart logique détecté : Absence de connecteurs logiques explicites"
    ],
    "logical_stru
... (tronqué)

    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `Flask - POST /api/fallacies`
- **Commande de Test :** `requests.post('http://127.0.0.1:8095/api/fallacies', json=...)`
- **Payload :**
  ```json
{
  "text": "Everyone is doing it, so it must be right."
}
  ```
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "category_distribution": {},
  "detection_options": {
    "categories": null,
    "include_context": true,
    "max_fallacies": 10,
    "severity_threshold": 0.5,
    "use_contextual": true,
    "use_enhanced": true,
    "use_patterns": true
  },
  "detection_timestamp": "Wed, 25 Jun 2025 03:05:22 GMT",
  "fallacies": [],
  "fallacy_count": 0,
  "processing_time": 0.0961761474609375,
  "severity_distribution": {
    "high": 0,
    "low": 0,
    "medium": 0
  },
  "success": true,
  "text_analyzed": "Everyone is doing it, so it must be right."
}
    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

### **Nom :** `Flask - POST /api/framework`
- **Commande de Test :** `requests.post('http://127.0.0.1:8095/api/framework', json=...)`
- **Payload :**
  ```json
{
  "arguments": [
    {
      "id": "a",
      "content": "Il faut réduire les impots.",
      "attacks": [
        "b"
      ]
    },
    {
      "id": "b",
      "content": "Réduire les impots va diminuer les recettes de l'Etat."
    },
    {
      "id": "c",
      "content": "C'est faux, la baisse des impots stimule la consommation.",
      "attacks": [
        "b"
      ]
    }
  ]
}
  ```
- **Réponse Obtenue :**
  - **Status:** 200
  - **Body:**
    ```json
{
  "argument_count": 3,
  "arguments": [
    {
      "attacked_by": [],
      "attacks": [
        "b"
      ],
      "content": "Il faut réduire les impots.",
      "id": "a",
      "status": "accepted",
      "supported_by": [],
      "supports": []
    },
    {
      "attacked_by": [
        "a",
        "c"
      ],
      "attacks": [],
      "content": "Réduire les impots va diminuer les recettes de l'Etat.",
      "id": "b",
      "status": "rejected",
      "supported_by": [],
      "supports": []
    },
    {
      "attacked_by": [],
      "attacks": [
        "b"
      ],
      "content": "C'est faux, la baisse des impots stimule la consommation.",
      "id": "c",
      "status": "accepted",
      "supported_by": [],
      "supports": []
    }
  ],
  "attack_count": 2,
  "attack_relations": [
    {
      "attacker": "a",
      "target": "b",
      "type": "attack"
    },
    {
      "attacker": "c",
      "target": "b",
      "type": "attack"
    }
  ],
  "extension_count": 
... (tronqué)

    ```
- **Résultat :** `SUCCÈS`
- **Corrections Apportées :** Aucune (phase de collecte).

