# Scripts de Test

Ce répertoire contient des scripts spécifiques pour des scénarios de test ou des simulations liés au projet d'analyse argumentative.

## Scripts Disponibles

- **`simulation_agent_informel.py`** : Script de simulation pour tester le comportement des agents informels dans différents contextes d'analyse.
- **`test_agent_informel.py`** : Script de test pour valider le fonctionnement des agents informels et leur capacité à analyser des arguments.

## Utilisation

### Simulation d'Agent Informel

Le script de simulation permet de tester le comportement d'un agent informel avec différents paramètres et dans différents contextes :

```bash
# Exécuter une simulation standard
python scripts/testing/simulation_agent_informel.py

# Exécuter une simulation avec des paramètres spécifiques
python scripts/testing/simulation_agent_informel.py --corpus exemples --niveau avance
```

### Test d'Agent Informel

Le script de test permet de valider le fonctionnement d'un agent informel :

```bash
# Exécuter les tests standards
python scripts/testing/test_agent_informel.py

# Exécuter les tests avec un niveau de détail élevé
python scripts/testing/test_agent_informel.py --verbose
```

## Intégration avec les Tests Unitaires

Ces scripts peuvent être utilisés en complément des tests unitaires pour valider le comportement des agents dans des scénarios plus complexes ou plus proches des conditions réelles d'utilisation.

Pour intégrer ces scripts dans une suite de tests plus large :

```bash
# Exécuter les tests unitaires puis les scripts de test
pytest tests/test_informal_agent.py && python scripts/testing/test_agent_informel.py
```

## Bonnes Pratiques

1. **Isolation** : Les scripts de test doivent être isolés et ne pas dépendre d'un état spécifique du système.
2. **Reproductibilité** : Les tests doivent être reproductibles et donner les mêmes résultats à chaque exécution.
3. **Documentation** : Chaque script doit documenter clairement ses paramètres et son comportement attendu.
4. **Validation** : Les scripts doivent inclure des mécanismes de validation pour vérifier que les résultats sont corrects.