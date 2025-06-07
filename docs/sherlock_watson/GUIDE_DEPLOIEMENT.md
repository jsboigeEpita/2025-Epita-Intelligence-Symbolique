# Guide Déploiement Oracle Enhanced v2.1.0

## 🎯 Vue d'ensemble Déploiement

### Environnements Supportés
- **Développement**: Local avec Conda
- **Test/Staging**: Docker + CI/CD
- **Production**: Kubernetes + monitoring

### Prérequis Système
- Python 3.9+
- Conda/Miniconda
- Git
- OpenAI API Key (pour GPT-4o-mini)
- 4GB RAM minimum, 8GB recommandé
- 2GB espace disque

## 🔧 Déploiement Local

### 1. Installation Complète
```bash
# Clone du projet
git clone <repository_url>
cd 2025-Epita-Intelligence-Symbolique

# Configuration environnement
powershell -File .\scripts\env\activate_project_env.ps1

# Validation installation
python -c "from argumentation_analysis.agents.core.oracle import get_oracle_version; print(f'Oracle Enhanced v{get_oracle_version()}')"
```

### 2. Configuration Variables d'Environnement
```bash
# Fichier .env (à créer)
OPENAI_API_KEY=your_openai_api_key_here
GLOBAL_LLM_SERVICE=OpenAI
OPENAI_CHAT_MODEL_ID=gpt-4o-mini
USE_REAL_JPYPE=true
JAVA_HOME=D:\2025-Epita-Intelligence-Symbolique\libs\portable_jdk\jdk-17.0.11+9
```

### 3. Tests de Validation
```bash
# Validation système Oracle
python scripts/maintenance/validate_oracle_coverage.py

# Tests complets
pytest tests/unit/argumentation_analysis/agents/core/oracle/ -v

# Démo fonctionnelle
python -m scripts.sherlock_watson.run_cluedo_oracle_enhanced
```

## 🐳 Déploiement Docker

### 1. Dockerfile Oracle Enhanced
```dockerfile
# Dockerfile
FROM python:3.9-slim

# Variables d'environnement
ENV PYTHONPATH=/app
ENV JAVA_HOME=/app/libs/portable_jdk/jdk-17.0.11+9
ENV USE_REAL_JPYPE=true

# Dépendances système
RUN apt-get update && apt-get install -y \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Application Oracle Enhanced
WORKDIR /app
COPY . .

# Installation dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installation Conda (minimal)
RUN wget -O miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash miniconda.sh -b -p /opt/conda \
    && rm miniconda.sh

# Environnement Conda Oracle
RUN /opt/conda/bin/conda env create -f environment.yml

# Port exposition (si web interface)
EXPOSE 8080

# Point d'entrée Oracle
CMD ["/opt/conda/envs/epita_symbolic_ai_sherlock/bin/python", "-m", "scripts.sherlock_watson.run_cluedo_oracle_enhanced"]
```

### 2. Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  oracle-enhanced:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GLOBAL_LLM_SERVICE=OpenAI
      - OPENAI_CHAT_MODEL_ID=gpt-4o-mini
    volumes:
      - ./logs:/app/logs
      - ./results:/app/results
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "python", "-c", "from argumentation_analysis.agents.core.oracle import get_oracle_version; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3

  oracle-tests:
    build: .
    command: ["python", "scripts/maintenance/validate_oracle_coverage.py"]
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - oracle-enhanced
```

### 3. Construction et Déploiement
```bash
# Construction image
docker build -t oracle-enhanced:v2.1.0 .

# Test local
docker run --env-file .env oracle-enhanced:v2.1.0

# Déploiement avec compose
docker-compose up -d

# Validation déploiement
docker-compose exec oracle-enhanced python scripts/maintenance/validate_oracle_coverage.py
```

## ☸️ Déploiement Kubernetes

### 1. Manifestes Kubernetes
```yaml
# oracle-enhanced-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oracle-enhanced
  labels:
    app: oracle-enhanced
    version: v2.1.0
spec:
  replicas: 2
  selector:
    matchLabels:
      app: oracle-enhanced
  template:
    metadata:
      labels:
        app: oracle-enhanced
    spec:
      containers:
      - name: oracle-enhanced
        image: oracle-enhanced:v2.1.0
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: oracle-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: oracle-enhanced-service
spec:
  selector:
    app: oracle-enhanced
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### 2. Configuration Secrets
```yaml
# oracle-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: oracle-secrets
type: Opaque
data:
  openai-api-key: <base64-encoded-key>
  
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: oracle-config
data:
  global-llm-service: "OpenAI"
  openai-chat-model-id: "gpt-4o-mini"
  use-real-jpype: "true"
```

### 3. Déploiement Kubernetes
```bash
# Application secrets et config
kubectl apply -f oracle-secrets.yaml

# Déploiement application
kubectl apply -f oracle-enhanced-deployment.yaml

# Vérification déploiement
kubectl get pods -l app=oracle-enhanced
kubectl logs -l app=oracle-enhanced

# Test service
kubectl port-forward service/oracle-enhanced-service 8080:80
```

## 🔍 Monitoring et Logging

### 1. Configuration Logging Production
```python
# config/logging_production.py
import logging
import logging.handlers
from pathlib import Path

def setup_production_logging():
    """Configuration logging production Oracle Enhanced"""
    
    # Dossier logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configuration root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Logger Oracle spécialisé
    oracle_logger = logging.getLogger("oracle")
    oracle_logger.setLevel(logging.DEBUG)
    
    # Handler fichier avec rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "oracle_enhanced.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Handler erreurs séparé
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "oracle_errors.log",
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    oracle_logger.addHandler(file_handler)
    oracle_logger.addHandler(error_handler)
    
    return oracle_logger
```

### 2. Métriques Prometheus
```python
# monitoring/oracle_metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Métriques Oracle Enhanced
oracle_requests_total = Counter('oracle_requests_total', 'Total Oracle requests', ['agent', 'query_type', 'status'])
oracle_request_duration = Histogram('oracle_request_duration_seconds', 'Oracle request duration')
oracle_active_agents = Gauge('oracle_active_agents', 'Number of active Oracle agents')
oracle_cache_hits = Counter('oracle_cache_hits_total', 'Oracle cache hits')
oracle_errors_total = Counter('oracle_errors_total', 'Oracle errors', ['error_type'])

class OracleMetricsCollector:
    """Collecteur métriques Oracle Enhanced"""
    
    def __init__(self, oracle_agent):
        self.oracle_agent = oracle_agent
        self.start_time = time.time()
        
    def record_request(self, agent_name: str, query_type: str, duration: float, success: bool):
        """Enregistre métriques requête Oracle"""
        status = "success" if success else "error"
        oracle_requests_total.labels(agent=agent_name, query_type=query_type, status=status).inc()
        oracle_request_duration.observe(duration)
        
    def record_error(self, error_type: str):
        """Enregistre erreur Oracle"""
        oracle_errors_total.labels(error_type=error_type).inc()
        
    def update_active_agents(self, count: int):
        """Met à jour nombre agents actifs"""
        oracle_active_agents.set(count)

# Démarrage serveur métriques
start_http_server(8000)
```

### 3. Configuration Alerting
```yaml
# alerting/oracle_alerts.yaml
groups:
- name: oracle_enhanced_alerts
  rules:
  - alert: OracleHighErrorRate
    expr: rate(oracle_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High Oracle error rate detected"
      description: "Oracle error rate is {{ $value }} errors/sec"
      
  - alert: OracleRequestLatency
    expr: histogram_quantile(0.95, oracle_request_duration_seconds) > 2.0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High Oracle request latency"
      description: "95th percentile latency is {{ $value }}s"
      
  - alert: OracleServiceDown
    expr: up{job="oracle-enhanced"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Oracle Enhanced service is down"
```

## 🚀 CI/CD Pipeline

### 1. GitHub Actions
```yaml
# .github/workflows/oracle-enhanced-ci.yml
name: Oracle Enhanced CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.9
        
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest-cov
        
    - name: Run Oracle tests
      run: |
        python scripts/maintenance/validate_oracle_coverage.py
        
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t oracle-enhanced:${{ github.sha }} .
        
    - name: Login to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        
    - name: Push image
      run: |
        docker tag oracle-enhanced:${{ github.sha }} myregistry/oracle-enhanced:${{ github.sha }}
        docker push myregistry/oracle-enhanced:${{ github.sha }}
        
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to staging
      run: |
        kubectl set image deployment/oracle-enhanced oracle-enhanced=myregistry/oracle-enhanced:${{ github.sha }}
```

### 2. Validation Déploiement
```bash
#!/bin/bash
# scripts/deployment/validate_deployment.sh

echo "🔍 Validation déploiement Oracle Enhanced..."

# Test santé service
if curl -f http://localhost:8080/health; then
    echo "✅ Service health check passed"
else
    echo "❌ Service health check failed"
    exit 1
fi

# Test couverture Oracle
if python scripts/maintenance/validate_oracle_coverage.py; then
    echo "✅ Oracle coverage validation passed"
else
    echo "❌ Oracle coverage validation failed"
    exit 1
fi

# Test démo fonctionnelle
if timeout 30s python -m scripts.sherlock_watson.run_cluedo_oracle_enhanced --test-mode; then
    echo "✅ Functional demo test passed"
else
    echo "❌ Functional demo test failed"
    exit 1
fi

echo "🎉 Déploiement Oracle Enhanced validé avec succès!"
```

## 📋 Checklist Déploiement

### ✅ Pré-déploiement
- [ ] Tests Oracle 100% (148/148) passent
- [ ] Variables d'environnement configurées
- [ ] Secrets OpenAI API configurés
- [ ] Resources système vérifiées (RAM, CPU, disque)
- [ ] Monitoring et logging configurés

### ✅ Déploiement
- [ ] Image Docker construite et testée
- [ ] Déploiement Kubernetes appliqué
- [ ] Services exposés et accessibles
- [ ] Health checks fonctionnels
- [ ] Métriques Prometheus collectées

### ✅ Post-déploiement
- [ ] Tests de validation exécutés
- [ ] Démonstration fonctionnelle validée
- [ ] Logs monitored pour erreurs
- [ ] Performance baseline établie
- [ ] Documentation mise à jour

---
*Guide Déploiement Oracle Enhanced v2.1.0 - Production Ready*
