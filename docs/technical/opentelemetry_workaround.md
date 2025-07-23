# Contournement du Conflit `jpype` et `opentelemetry`

Ce document détaille la solution de contournement mise en place pour résoudre un conflit critique entre les bibliothèques `jpype` et `opentelemetry` qui provoquait un crash de la machine virtuelle Java (JVM).

## Le Problème

L'utilisation simultanée de `jpype` (pour l'intégration Java) et de `opentelemetry` (pour la télémétrie) entraînait des conflits de bas niveau, menant à une instabilité et à des crashs de la JVM. Pour garantir la stabilité de l'application, la décision a été prise de neutraliser `opentelemetry`.

## Stratégie de Contournement

La stratégie consiste à remplacer les paquets `opentelemetry` par des paquets factices (dummy packages). Ces paquets contiennent des classes et des fonctions vides qui satisfont les importations requises par d'autres bibliothèques, comme `semantic-kernel`, sans charger le code `opentelemetry` réel.

Le répertoire `dummy_opentelemetry` a été ajouté au `PYTHONPATH` pour que l'interpréteur Python le trouve avant les paquets `opentelemetry` installés.

## Objets Factices Implémentés

Pour résoudre les `ImportError` successives, les objets factices suivants ont été créés :

### Dans `dummy_opentelemetry/opentelemetry-api/opentelemetry/trace/__init__.py`

*   `Span`: Classe factice représentant une trace.
*   `Tracer`: Classe factice pour créer des `Span`.
*   `get_tracer()`: Fonction factice retournant un `Tracer`.
*   `use_span()`: Décorateur factice.
*   `StatusCode`: Classe factice contenant des codes de statut.

### Dans `dummy_opentelemetry/opentelemetry-api/opentelemetry/metrics.py`

*   `Meter`: Classe factice pour créer des compteurs et des histogrammes.
*   `MeterProvider`: Classe factice pour fournir un `Meter`.
*   `get_meter_provider()`: Fonction factice retournant un `MeterProvider`.
*   `Histogram`: Classe factice pour les histogrammes.

### Dans `dummy_opentelemetry/opentelemetry-api/opentelemetry/__init__.py`

Ce fichier assure que les modules `trace` et `metrics` sont correctement importables depuis le package `opentelemetry`.