# Bibliothèques Natives

Ce répertoire contient les bibliothèques natives (DLL) utilisées par le système d'analyse argumentative pour les fonctionnalités de résolution de problèmes de satisfiabilité.

## Contenu du Répertoire

### lingeling.dll
Implémentation du solveur SAT Lingeling, un solveur de satisfiabilité booléenne hautement optimisé développé par Armin Biere.

### minisat.dll
Implémentation du solveur SAT MiniSat, un solveur de satisfiabilité booléenne minimaliste mais efficace développé par Niklas Eén et Niklas Sörensson.

### picosat.dll
Implémentation du solveur SAT PicoSAT, un solveur de satisfiabilité booléenne compact développé par Armin Biere.

## Utilisation

Ces bibliothèques natives sont utilisées par le système via l'interface JVM fournie par JPype. Elles sont chargées automatiquement lors de l'initialisation du service JVM.

```python
from argumentation_analysis.services.jvm_service import JVMService

# Initialisation du service JVM qui chargera les bibliothèques natives
jvm_service = JVMService()
jvm_service.initialize()

# Utilisation d'un solveur SAT via Tweety
sat_solver = jvm_service.get_class("org.tweetyproject.logics.pl.sat.Sat4jSolver")()
```

## Prérequis

- **Windows x64** : Ces bibliothèques sont compilées pour Windows 64 bits
- **Java JDK 11+** : Nécessaire pour l'interface JVM

## Dépannage

Si vous rencontrez des erreurs liées au chargement des bibliothèques natives :

1. Vérifiez que le chemin vers ce répertoire est correctement configuré dans les paramètres du système
2. Assurez-vous que vous utilisez une version 64 bits de Windows
3. Vérifiez que les DLL ne sont pas bloquées par le système d'exploitation (clic droit > Propriétés > Débloquer)
4. Assurez-vous que les dépendances système requises sont installées (Visual C++ Redistributable)

## Compilation

Si vous avez besoin de recompiler ces bibliothèques pour une autre plateforme :

1. Téléchargez le code source des solveurs SAT correspondants
2. Suivez les instructions de compilation spécifiques à chaque solveur
3. Placez les bibliothèques compilées dans ce répertoire
4. Mettez à jour la configuration du service JVM si nécessaire

## Ressources Associées

- [Documentation Tweety](https://tweetyproject.org/doc/)
- [Service JVM](../../argumentation_analysis/services/README.md)
- [Bibliothèques Externes](../README.md)