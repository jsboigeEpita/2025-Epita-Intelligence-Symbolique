# Procédure de Rollback en Cas d'Incident de Production

## 1. Introduction

Cette procédure décrit les étapes à suivre pour revenir rapidement à une version stable de l'application en cas d'incident majeur survenant après un déploiement en production. Un incident majeur peut inclure, sans s'y limiter :

*   Une augmentation critique du taux d'erreur (5xx) signalée par le système de monitoring.
*   Un crash ou un comportement instable de l'application principale.
*   Une régression fonctionnelle critique identifiée après le déploiement.

L'objectif est de minimiser le temps de résolution de l'incident (MTTR) en restaurant un service fiable pour les utilisateurs.

## 2. Prérequis

Pour qu'un rollback soit possible, les conditions suivantes doivent être remplies :

*   **Registre d'Images Docker :** Toutes les images Docker doivent être poussées vers un registre de conteneurs (ex: GitHub Container Registry, Docker Hub) qui conserve les versions précédentes.
*   **Versioning Sémantique des Images :** Chaque image poussée dans le registre doit être taguée avec un identifiant unique et immuable. Conformément au plan opérationnel, nous utilisons l'identifiant de commit Git (`github.sha`) qui a déclenché la construction de l'image. Un tag comme `my-app:a1b2c3d` garantit une traçabilité parfaite entre l'image et le code source.

## 3. Procédure de Rollback Manuel

Cette procédure est conçue pour être exécutée manuellement par l'équipe technique en cas d'urgence.

### 3.1. Identifier la Version Stable

1.  **Consulter l'historique des commits :** Rendez-vous sur l'historique Git de la branche `main`.
2.  **Identifier le dernier commit stable :** Repérez le commit qui correspond à la dernière version connue pour être stable en production avant le déploiement défectueux.
3.  **Copier l'identifiant du commit (SHA) :** Copiez l'identifiant complet de ce commit (ex: `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0`).

### 3.2. Redéployer l'Image Stable

Le redéploiement s'effectue en déclenchant un workflow manuel dans GitHub Actions.

1.  **Accéder à l'onglet "Actions"** du dépôt GitHub.
2.  Dans la liste des workflows, sélectionnez **"CI Pipeline"**.
3.  Cliquez sur le bouton **"Run workflow"**.
4.  Sélectionnez le job **`rollback-production`** (Note : ce job doit être créé conformément au plan opérationnel).
5.  Dans le champ d'input, collez l'**identifiant du commit (SHA)** de la version stable que vous avez identifié.
6.  Lancez le workflow.

Le pipeline se chargera de tirer l'image Docker correspondante depuis le registre et de la redéployer, en remplaçant la version instable.

### 3.3. Vérification Post-Rollback

Une fois le workflow de rollback terminé, il est crucial de vérifier que le système est revenu à un état stable.

1.  **Monitoring :** Surveillez attentivement les tableaux de bord de monitoring (Grafana, Datadog...). Le taux d'erreur doit revenir à la normale.
2.  **Tests de Santé (Health Checks) :** Assurez-vous que les points de terminaison de santé de l'application répondent correctement.
3.  **Validation Manuelle :** Effectuez quelques vérifications manuelles sur les fonctionnalités clés de l'application pour confirmer qu'elles sont de nouveau opérationnelles.

## 4. Communication d'Incident

Une communication claire est essentielle pendant un incident.

*   **Qui informer :**
    *   L'équipe de développement.
    *   Le Product Owner / Chef de projet.
*   **Canal de communication :**
    *   Un canal de discussion dédié (ex: Slack `#incidents-prod`).
*   **Messages clés :**
    1.  **Début de l'incident :** "Incident en production détecté. Investigation en cours."
    2.  **Début du rollback :** "Déclenchement de la procédure de rollback vers la version `[SHA du commit]`."
    3.  **Fin de l'incident :** "Rollback terminé. Le système est de nouveau opérationnel. Une analyse post-mortem sera effectuée."
