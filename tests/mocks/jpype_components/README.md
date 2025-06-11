# Mocks pour les Composants JPype

## Objectif

Ce répertoire contient les modules de simulation (mocks) pour les composants internes de **JPype**. L'objectif est de fournir un environnement de test léger et contrôlé qui imite le comportement de JPype, sans nécessiter une véritable machine virtuelle Java (JVM). Cela est particulièrement utile pour les tests unitaires qui dépendent de bibliothèques Java via JPype, comme la suite Tweety.

## Composants Mockés

Le mock est décomposé en plusieurs fichiers, chacun simulant une partie spécifique de l'API de JPype :

*   **`jclass_core.py`**: Simule le cœur de la création de classes Java (`JClass`). Il utilise `unittest.mock.MagicMock` pour générer des classes et des instances Java à la volée. Il contient une logique spécifique pour des classes système (`java.lang.ClassLoader`, `java.lang.System`) et pour les classes de la bibliothèque Tweety (`ModalLogic`, `CompleteReasoner`, etc.).
*   **`jvm.py`**: Simule le cycle de vie de la JVM (`startJVM`, `shutdownJVM`, `isJVMStarted`). Il maintient un état interne pour savoir si la JVM est "démarrée" et gère les chemins de la JVM et du classpath.
*   **`config.py`**: Simule l'objet de configuration de JPype, permettant de définir des paramètres comme le chemin de la JVM ou la conversion de chaînes de caractères.
*   **`imports.py`**: Simule le mécanisme d'importation de JPype, permettant d'importer des classes Java comme si elles étaient des modules Python.
*   **`types.py`**: Fournit des simulations pour les types de données primitifs et les collections Java (`JString`, `JArray`, `MockJavaCollection`, etc.), en assurant une conversion et un comportement similaires aux types Java réels.
*   **`exceptions.py`**: Définit des exceptions simulées (`JException`, `JVMNotFoundException`) pour imiter les erreurs que JPype peut lever.
*   **`tweety_*.py`**: Ces fichiers (`tweety_agents.py`, `tweety_enums.py`, `tweety_reasoners.py`, `tweety_syntax.py`, `tweety_theories.py`) contiennent la logique de simulation spécifique à la bibliothèque Tweety. Ils configurent les mocks pour les classes et les énumérations de Tweety afin qu'ils se comportent comme prévu dans les tests.

## Utilisation

Ces mocks sont orchestrés par le fichier `tests/mocks/jpype_mock.py`. Pour les utiliser dans les tests, il suffit de remplacer l'importation de `jpype` par une importation de `tests.mocks.jpype_mock`.

Le point d'entrée principal est la fonction `JClass("nom.de.la.classe.Java")`, qui retourne une classe Java simulée. Les instances de cette classe peuvent ensuite être utilisées pour appeler des méthodes (qui seront des `MagicMock`) et interagir avec l'écosystème simulé.

**Exemple :**

```python
# Dans un fichier de test
from tests.mocks import jpype_mock as jpype

# Démarrer la JVM simulée
jpype.startJVM()

# Obtenir une classe Java simulée
DungTheory = jpype.JClass("net.sf.tweety.arg.dung.syntax.DungTheory")

# Créer une instance
theory_instance = DungTheory()

# Appeler une méthode (qui sera une MagicMock)
theory_instance.add("a")

# Vérifier un appel
theory_instance.add.assert_called_with("a")
