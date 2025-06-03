# Scripts d'Exécution

Ce répertoire contient les scripts d'exécution utilisés pour lancer et tester les agents du système d'analyse d'argumentation.

## Structure

- `test/` - Scripts pour l'exécution des tests automatisés
- `deploy/` - Scripts pour le déploiement des agents
- `integration/` - Scripts pour les tests d'intégration

## Utilisation

Ces scripts sont conçus pour faciliter l'exécution des agents dans différents contextes (test, déploiement, intégration). Ils fournissent des interfaces standardisées pour interagir avec les agents.

### Scripts de test

Les scripts de test permettent de vérifier le bon fonctionnement des agents individuellement ou en combinaison. Ils incluent des tests unitaires et des tests d'intégration.

Exemples d'utilisation :
- Test d'un agent spécifique avec des entrées contrôlées
- Vérification de la cohérence des résultats
- Tests de régression après des modifications
- Tests de performance

### Scripts de déploiement

Les scripts de déploiement permettent de déployer les agents dans différents environnements (développement, production, etc.).

Exemples d'utilisation :
- Préparation des agents pour le déploiement
- Configuration des environnements
- Vérification des dépendances
- Déploiement automatisé

### Scripts d'intégration

Les scripts d'intégration permettent de tester l'interaction entre les différents agents et avec d'autres systèmes.

Exemples d'utilisation :
- Tests d'orchestration complète
- Tests à grande échelle
- Simulation de scénarios complexes
- Évaluation des performances du système complet

## Exécution des scripts

Pour exécuter un script, utilisez la commande Python standard :

```bash
python agents/runners/[catégorie]/[script].py
```

Par exemple, pour exécuter un test d'agent informel :

```bash
python agents/runners/test/informal/test_informal_agent.py
```

## Création de nouveaux scripts

Pour créer un nouveau script d'exécution :

1. Identifiez la catégorie appropriée (test, deploy, integration)
2. Créez un nouveau fichier Python dans le répertoire correspondant
3. Suivez la structure standard des scripts existants
4. Documentez clairement l'objectif et l'utilisation du script
