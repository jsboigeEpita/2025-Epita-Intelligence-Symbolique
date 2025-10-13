# 🔗 Integrations

## Description

Ce répertoire contient des exemples d'intégration du système d'argumentation avec des systèmes externes et des architectures distribuées. Ces exemples démontrent comment connecter le système à des backends, APIs externes, microservices, et infrastructures cloud.

## Contenu

### Sous-Répertoires

| Répertoire | Description | Complexité | Scripts Clés |
|------------|-------------|------------|--------------|
| **[backend_demos/](./backend_demos/)** | Démonstrations d'intégration backend | Intermédiaire | backend_mock_demo.py |

## 🔌 Backend Demos

**Objectif** : Démontrer l'intégration du système avec des backends et services externes

### Fichiers

| Fichier | Description | Lignes |
|---------|-------------|--------|
| [`backend_mock_demo.py`](./backend_demos/backend_mock_demo.py) | Démo avec backend mocké (140 lignes) | 140 |

### Fonctionnalités Démontrées

- ✅ **API REST Integration** : Connexion à des APIs REST
- ✅ **Mock Services** : Simulation de services externes pour tests
- ✅ **Error Handling** : Gestion robuste des erreurs réseau
- ✅ **Retry Logic** : Réessai automatique en cas d'échec
- ✅ **Circuit Breaker** : Protection contre les cascades d'erreurs
- ✅ **Response Caching** : Cache des réponses pour performance

### Utilisation

```bash
# Naviguer vers le répertoire
cd examples/03_integrations/backend_demos

# Exécuter la démo avec backend mocké
python backend_mock_demo.py

# Avec backend réel (nécessite configuration)
python backend_mock_demo.py --real-backend --api-url https://api.example.com
```

### Ce Que Vous Apprendrez

- ✅ Intégrer le système avec des APIs REST
- ✅ Implémenter un pattern Mock pour les tests
- ✅ Gérer les erreurs réseau gracieusement
- ✅ Optimiser les performances avec cache
- ✅ Monitorer les intégrations

**📖 [Code source](./backend_demos/backend_mock_demo.py)**

## Patterns d'Intégration

### 1. API REST

**Pattern classique** pour intégration HTTP/HTTPS

```python
import requests
from typing import Dict, Any

class BackendClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Envoie un texte au backend pour analyse"""
        response = requests.post(
            f"{self.base_url}/api/analyze",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"text": text}
        )
        response.raise_for_status()
        return response.json()
```

### 2. Mock Services

**Pattern pour tests** sans dépendances externes

```python
class MockBackend:
    """Backend simulé pour tests"""
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Simule une analyse"""
        return {
            "fallacies": [
                {"type": "ad_hominem", "confidence": 0.85}
            ],
            "sentiment": "neutral",
            "complexity": "medium"
        }
```

### 3. Retry with Exponential Backoff

**Pattern de résilience** pour réseaux instables

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1):
    """Décorateur pour retry avec backoff exponentiel"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
def call_api(endpoint):
    """Appel API avec retry automatique"""
    return requests.get(endpoint)
```

### 4. Circuit Breaker

**Pattern de protection** contre les services défaillants

```python
class CircuitBreaker:
    """Implémentation simple de circuit breaker"""
    
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

## Architecture d'Intégration

### Vue d'Ensemble

```
┌─────────────────────────────────────────┐
│  Système d'Argumentation (Client)      │
├─────────────────────────────────────────┤
│  BackendClient                          │
│  ├─ Retry Logic                         │
│  ├─ Circuit Breaker                     │
│  └─ Response Cache                      │
└──────────────┬──────────────────────────┘
               │ HTTP/REST
               ↓
┌─────────────────────────────────────────┐
│  API Gateway / Load Balancer           │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       ↓               ↓
┌─────────────┐ ┌─────────────┐
│  Backend 1  │ │  Backend 2  │
│  Service    │ │  Service    │
└─────────────┘ └─────────────┘
```

### Composants

1. **Client Layer** : Logique d'intégration côté système
2. **Resilience Layer** : Retry, circuit breaker, timeout
3. **Communication Layer** : HTTP, gRPC, WebSocket
4. **Gateway Layer** : Load balancing, routing, authentication
5. **Backend Services** : Services externes intégrés

## Cas d'Usage

### 1. Analyse Distribuée

**Scénario** : Distribuer l'analyse sur plusieurs backends

```python
import asyncio
from typing import List

async def distributed_analysis(text: str, backends: List[BackendClient]):
    """Distribue l'analyse sur plusieurs backends"""
    
    # Créer les tâches
    tasks = [
        backend.analyze_text(text)
        for backend in backends
    ]
    
    # Exécuter en parallèle
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Agréger les résultats
    aggregated = aggregate_results(results)
    
    return aggregated
```

### 2. Fallback Strategy

**Scénario** : Basculer sur un backend de secours si le principal échoue

```python
def analyze_with_fallback(text: str, primary: BackendClient, fallback: BackendClient):
    """Analyse avec fallback automatique"""
    try:
        return primary.analyze_text(text)
    except Exception as e:
        print(f"Primary backend failed: {e}")
        print("Falling back to secondary backend...")
        return fallback.analyze_text(text)
```

### 3. Caching Strategy

**Scénario** : Mettre en cache les résultats pour éviter les appels répétés

```python
import hashlib
import json
from functools import lru_cache

class CachedBackendClient:
    """Client backend avec cache"""
    
    def __init__(self, backend: BackendClient, cache_size=128):
        self.backend = backend
        self._cache = {}
    
    def analyze_text(self, text: str):
        """Analyse avec cache"""
        # Calculer hash du texte
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Vérifier le cache
        if text_hash in self._cache:
            return self._cache[text_hash]
        
        # Appeler le backend
        result = self.backend.analyze_text(text)
        
        # Mettre en cache
        self._cache[text_hash] = result
        
        return result
```

## Tests d'Intégration

### Configuration

```bash
# Installer les dépendances de test
pip install pytest pytest-asyncio pytest-mock requests-mock

# Exécuter les tests
pytest examples/03_integrations/backend_demos/test_*.py
```

### Exemple de Test

```python
import pytest
from backend_demos.backend_mock_demo import MockBackend

def test_mock_backend_analyze():
    """Test du backend mocké"""
    backend = MockBackend()
    result = backend.analyze_text("Test d'analyse")
    
    assert "fallacies" in result
    assert isinstance(result["fallacies"], list)
    assert result["sentiment"] in ["positive", "negative", "neutral"]

@pytest.mark.asyncio
async def test_distributed_analysis():
    """Test de l'analyse distribuée"""
    backends = [MockBackend(), MockBackend()]
    result = await distributed_analysis("Test", backends)
    
    assert result is not None
    assert "aggregated_fallacies" in result
```

## Performance

### Métriques Typiques

| Métrique | Sans Cache | Avec Cache | Amélioration |
|----------|------------|------------|--------------|
| Latency moyenne | 200ms | 10ms | 20x |
| Throughput | 50 req/s | 500 req/s | 10x |
| Taux d'erreur | 2% | 0.1% | 20x |
| Coût API | $100/jour | $20/jour | 5x |

### Optimisations

1. **Connection Pooling** : Réutiliser les connexions HTTP
2. **Request Batching** : Grouper les requêtes
3. **Parallel Requests** : Exécuter en parallèle
4. **Response Compression** : Compresser les réponses
5. **CDN Integration** : Utiliser un CDN pour les assets statiques

## Monitoring et Observabilité

### Métriques à Surveiller

```python
import time
from prometheus_client import Counter, Histogram

# Métriques Prometheus
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration'
)

def monitored_request(method, endpoint):
    """Requête avec monitoring"""
    start_time = time.time()
    try:
        response = requests.request(method, endpoint)
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        return response
    finally:
        duration = time.time() - start_time
        api_request_duration.observe(duration)
```

### Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_api_call(endpoint, response_time, status):
    """Log d'appel API structuré"""
    logger.info(
        "API call",
        extra={
            "endpoint": endpoint,
            "response_time_ms": response_time * 1000,
            "status_code": status,
            "timestamp": time.time()
        }
    )
```

## Sécurité

### Bonnes Pratiques

1. **API Keys** : Stocker dans variables d'environnement
2. **HTTPS Only** : Toujours utiliser HTTPS
3. **Rate Limiting** : Respecter les limites
4. **Input Validation** : Valider toutes les entrées
5. **Error Messages** : Ne pas exposer d'informations sensibles

### Exemple Sécurisé

```python
import os
from cryptography.fernet import Fernet

class SecureBackendClient:
    """Client backend sécurisé"""
    
    def __init__(self):
        # API key depuis variable d'environnement
        self.api_key = os.getenv("BACKEND_API_KEY")
        if not self.api_key:
            raise ValueError("BACKEND_API_KEY not set")
        
        # Encryption pour données sensibles
        self.cipher = Fernet(os.getenv("ENCRYPTION_KEY").encode())
    
    def send_sensitive_data(self, data: str):
        """Envoie de données chiffrées"""
        encrypted = self.cipher.encrypt(data.encode())
        return self._post("/api/secure", encrypted)
```

## Déploiement

### Docker

```dockerfile
# Dockerfile pour intégration
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend_demos/ ./backend_demos/

ENV BACKEND_API_URL=https://api.example.com
ENV BACKEND_API_KEY=your-api-key

CMD ["python", "backend_demos/backend_mock_demo.py"]
```

### Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argumentation-integration
spec:
  replicas: 3
  selector:
    matchLabels:
      app: argumentation
  template:
    metadata:
      labels:
        app: argumentation
    spec:
      containers:
      - name: integration
        image: argumentation-integration:latest
        env:
        - name: BACKEND_API_URL
          valueFrom:
            configMapKeyRef:
              name: integration-config
              key: api-url
        - name: BACKEND_API_KEY
          valueFrom:
            secretKeyRef:
              name: integration-secrets
              key: api-key
```

## Ressources Connexes

- **[Core System Demos](../02_core_system_demos/)** : Démos système central
- **[Plugins](../04_plugins/)** : Architecture extensible
- **[Integration Demos](../../demos/integration/)** : Tests d'intégration
- **[Documentation](../../docs/)** : Référence complète

## Contribution

### Ajouter une Nouvelle Intégration

1. **Créer le client** dans `backend_demos/`
2. **Implémenter les patterns** : retry, circuit breaker, cache
3. **Écrire les tests** : unitaires et d'intégration
4. **Documenter** : README + docstrings
5. **Exemple d'usage** : Script de démonstration

### Template

```python
#!/usr/bin/env python3
"""
Integration: [Nom du Service]
Description: Intégration avec [service externe]
"""

class ServiceClient:
    """Client pour intégration avec [Service]"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    def analyze(self, text: str):
        """Analyse via service externe"""
        # Implémentation
        pass

if __name__ == "__main__":
    # Démo
    client = ServiceClient("https://api.service.com", "key")
    result = client.analyze("Test")
    print(result)
```

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA  
**Niveau** : Intermédiaire à Avancé  
**Technologies** : Python, REST API, Docker, Kubernetes