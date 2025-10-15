from unittest.mock import MagicMock
import logging
import sys

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[MOCK JPYPE TYPES LOG] %(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

from .jclass_core import MockJClassCore

# Remplacer l'utilisation du placeholder par la vraie classe MockJClassCore
# Nous utiliserons un alias JClass pour la lisibilité et la compatibilité sémantique.
JClass = MockJClassCore


class _ModuleLevelMockJavaIterator:
    def __init__(self, collection):
        self._iterator = iter(collection)
        self._next_item = None
        self._has_next_item = False
        self._advance()

    def _advance(self):
        try:
            self._next_item = next(self._iterator)
            self._has_next_item = True
        except StopIteration:
            self._has_next_item = False

    def hasNext(self):
        return self._has_next_item

    def next(self):
        if not self._has_next_item:
            # En Java, cela lèverait java.util.NoSuchElementException
            # JPype pourrait le convertir en StopIteration ou une exception JPype spécifique.
            # Pour la cohérence avec l'itération Python, StopIteration est ok ici.
            raise StopIteration("No more elements in mock Java iterator")
        current_item = self._next_item
        self._advance()
        return current_item


class MockJavaCollection:  # Ne pas faire hériter de MockJClassCore ici.
    def __init__(self, java_class_name, *constructor_args):
        self.class_name = java_class_name
        self._constructor_args = constructor_args
        self._internal_collection = self._determine_internal_collection_type()
        mock_logger.debug(
            f"MockJavaCollection '{self.class_name}' créée. Args: {constructor_args}"
        )

        if constructor_args:
            initial_data = constructor_args[0]
            if hasattr(initial_data, "__iter__"):
                try:
                    if hasattr(initial_data, "iterator") and callable(
                        initial_data.iterator
                    ):
                        it = initial_data.iterator()
                        while it.hasNext():
                            self.add(it.next())
                    else:
                        for item in initial_data:
                            self.add(item)
                except TypeError:
                    mock_logger.warning(
                        f"MockJavaCollection pour {self.class_name} a reçu un argument de constructeur non itérable: {initial_data}"
                    )
            elif initial_data is not None:
                mock_logger.warning(
                    f"MockJavaCollection pour {self.class_name} a reçu un argument de constructeur non-collection: {initial_data}"
                )

    def _determine_internal_collection_type(self):
        # TODO: Affiner pour MockJavaList, MockJavaSet, MockJavaMap
        if (
            "Map" in self.class_name
            or "HashMap" in self.class_name
            or "LinkedHashMap" in self.class_name
        ):
            return {}
        if (
            "Set" in self.class_name
            or "HashSet" in self.class_name
            or "TreeSet" in self.class_name
        ):  # TreeSet impliquerait un tri
            return set()
        # Pour l'instant, tout le reste est une liste (List, ArrayList, LinkedList, Queue, Deque)
        return []

    def add(self, element):  # Pour Collection et List
        if isinstance(self._internal_collection, list):
            self._internal_collection.append(element)
            return True  # List.add toujours True
        elif isinstance(self._internal_collection, set):
            is_new = element not in self._internal_collection
            self._internal_collection.add(element)
            return is_new  # Set.add retourne si l'élément a été ajouté (nouveau)
        elif isinstance(self._internal_collection, dict):
            raise NotImplementedError(
                f"Utilisez put(key, value) pour les Maps, pas add(). Classe: {self.class_name}"
            )
        return False

    def put(self, key, value):  # Pour Map
        if not isinstance(self._internal_collection, dict):
            raise TypeError(
                f"put() n'est supporté que par les Maps. Classe: {self.class_name}"
            )
        old_value = self._internal_collection.get(key)
        self._internal_collection[key] = value
        return old_value  # Map.put retourne l'ancienne valeur ou null

    def get(self, key_or_index):  # Pour Map (key) ou List (index)
        if isinstance(self._internal_collection, dict):  # Map.get(key)
            return self._internal_collection.get(
                key_or_index
            )  # Retourne null si la clé n'existe pas
        elif isinstance(self._internal_collection, list):  # List.get(index)
            if not isinstance(key_or_index, int):
                raise TypeError("L'index pour List.get() doit être un entier.")
            if 0 <= key_or_index < len(self._internal_collection):
                return self._internal_collection[key_or_index]
            else:
                # En Java: IndexOutOfBoundsException
                raise IndexError(
                    f"Index hors limites: {key_or_index} pour une liste de taille {len(self._internal_collection)}"
                )
        else:
            raise TypeError(f"get() non supporté par {self.class_name}")

    def size(self):
        s = len(self._internal_collection)
        mock_logger.debug(
            f"MockJavaCollection '{self.class_name}'.size() -> {s}. Contenu: {self._internal_collection}"
        )
        return s

    def isEmpty(self):
        return len(self._internal_collection) == 0

    def contains(self, element):  # Pour Collection (List, Set)
        if isinstance(self._internal_collection, dict):
            raise NotImplementedError(
                f"Utilisez containsKey() ou containsValue() pour les Maps. Classe: {self.class_name}"
            )
        if hasattr(element, "equals") and callable(element.equals):
            for item in self._internal_collection:
                if element.equals(item):
                    return True
            return False
        return element in self._internal_collection

    def containsKey(self, key):  # Pour Map
        if not isinstance(self._internal_collection, dict):
            raise TypeError(
                f"containsKey() n'est supporté que par les Maps. Classe: {self.class_name}"
            )
        return key in self._internal_collection

    def containsValue(self, value):  # Pour Map
        if not isinstance(self._internal_collection, dict):
            raise TypeError(
                f"containsValue() n'est supporté que par les Maps. Classe: {self.class_name}"
            )
        # Doit utiliser .equals() pour comparer les valeurs si elles sont des objets Java mockés
        for v_item in self._internal_collection.values():
            if hasattr(value, "equals") and callable(value.equals):
                if value.equals(v_item):
                    return True
            elif value == v_item:  # Fallback
                return True
        return False

    def remove(self, element_or_key):  # Pour Collection (element) ou Map (key)
        try:
            if isinstance(self._internal_collection, list):
                item_to_remove = None
                for item in self._internal_collection:
                    if hasattr(element_or_key, "equals") and callable(
                        element_or_key.equals
                    ):
                        if element_or_key.equals(item):
                            item_to_remove = item
                            break
                    elif element_or_key == item:
                        item_to_remove = item
                        break
                if item_to_remove is not None:
                    self._internal_collection.remove(item_to_remove)
                    return True  # List.remove(Object) retourne true si l'élément était présent
                return False
            elif isinstance(self._internal_collection, set):
                if element_or_key in self._internal_collection:
                    self._internal_collection.remove(element_or_key)
                    return True  # Set.remove(Object) retourne true si l'élément était présent
                return False
            elif isinstance(self._internal_collection, dict):  # Map.remove(key)
                if element_or_key in self._internal_collection:
                    old_value = self._internal_collection.pop(element_or_key)
                    return old_value  # Map.remove(key) retourne la valeur associée, ou null
                return None  # Si la clé n'est pas trouvée
        except (
            ValueError
        ):  # remove sur une liste peut lever ValueError si non trouvé (ne devrait pas arriver avec la logique ci-dessus)
            return False
        return False  # Fallback pour List/Set si non trouvé

    def clear(self):
        self._internal_collection.clear()

    def __iter__(
        self,
    ):  # Pour itération Python directe sur le mock (sur les éléments pour List/Set, sur les clés pour Map)
        if isinstance(self._internal_collection, dict):
            return iter(self._internal_collection.keys())
        return iter(self._internal_collection)

    def iterator(self):  # Méthode Java iterator() pour Collection (List, Set)
        if isinstance(self._internal_collection, dict):
            # Map n'a pas de méthode iterator() directe, mais keySet().iterator(), values().iterator(), entrySet().iterator()
            raise TypeError(
                f"Map ({self.class_name}) n'a pas de méthode iterator() directe. Utilisez keySet().iterator() etc."
            )
        return _ModuleLevelMockJavaIterator(self._internal_collection)

    def keySet(self):  # Pour Map
        if not isinstance(self._internal_collection, dict):
            raise TypeError(
                f"keySet() n'est supporté que par les Maps. Classe: {self.class_name}"
            )
        # Retourne un MockJavaSet contenant les clés
        # Nécessite que JClass soit disponible ou une façon de créer MockJavaSet
        # Pour l'instant, on retourne un set Python, ce qui n'est pas idéal pour le mock.
        # Idéalement: return MockJavaSet("java.util.Set", self._internal_collection.keys())
        # Pour cela, MockJavaSet doit être défini et importable.
        # Temporairement:
        mock_set = MockJavaCollection("java.util.HashSet")  # Simule un Set de clés
        for key in self._internal_collection.keys():
            mock_set.add(key)
        return mock_set

    def values(self):  # Pour Map
        if not isinstance(self._internal_collection, dict):
            raise TypeError(
                f"values() n'est supporté que par les Maps. Classe: {self.class_name}"
            )
        # Retourne une Collection (souvent non spécifiée, peut être une List) des valeurs
        # Idéalement: return MockJavaCollection("java.util.Collection", self._internal_collection.values())
        # Temporairement:
        mock_coll = MockJavaCollection(
            "java.util.ArrayList"
        )  # Simule une Collection de valeurs
        for value in self._internal_collection.values():
            mock_coll.add(value)
        return mock_coll

    # entrySet() pour Map est plus complexe car il retourne un Set<Map.Entry<K,V>>
    # Map.Entry est une interface. Il faudrait MockMapEntry.

    def toString(self):
        if isinstance(self._internal_collection, list):
            return (
                "[" + ", ".join(str(item) for item in self._internal_collection) + "]"
            )
        elif isinstance(self._internal_collection, set):
            # L'ordre n'est pas garanti pour les sets, mais Python set str() est ok pour le mock
            return str(self._internal_collection) if self._internal_collection else "[]"
        elif isinstance(self._internal_collection, dict):
            # Format Java: {key1=value1, key2=value2}
            if not self._internal_collection:
                return "{}"
            return (
                "{"
                + ", ".join(
                    f"{str(k)}={str(v)}" for k, v in self._internal_collection.items()
                )
                + "}"
            )
        return str(list(self._internal_collection))  # Fallback

    def equals(self, other):
        if not isinstance(other, MockJavaCollection):
            return False

        # Comparaison des types de collection sous-jacents
        if type(self._internal_collection) != type(other._internal_collection):
            return False
        if self.size() != other.size():
            return False

        if isinstance(self._internal_collection, list):  # List equals
            for item_self, item_other in zip(
                self._internal_collection, other._internal_collection
            ):
                equals_method_self = getattr(item_self, "equals", None)
                if callable(equals_method_self):
                    if not equals_method_self(item_other):
                        return False
                elif item_self != item_other:
                    return False
            return True
        elif isinstance(self._internal_collection, set):  # Set equals
            # Vérifier que other._internal_collection contient tous les éléments de self._internal_collection
            # en utilisant la méthode contains de l'autre set (qui devrait utiliser .equals)
            # ou en comparant directement les sets Python si les éléments sont hashables et .equals est cohérent.
            # Pour un mock, la comparaison directe des sets Python est souvent suffisante si les éléments sont bien mockés.
            return (
                self._internal_collection == other._internal_collection
            )  # Suppose que les éléments ont __eq__ et __hash__ corrects
        elif isinstance(self._internal_collection, dict):  # Map equals
            # Deux maps sont égales si elles représentent le même ensemble de paires clé-valeur.
            # L'ordre n'importe pas.
            if len(self._internal_collection) != len(other._internal_collection):
                return False  # Redondant avec size()
            for k_self, v_self in self._internal_collection.items():
                if k_self not in other._internal_collection:
                    return False
                v_other = other._internal_collection[k_self]

                equals_method_v_self = getattr(v_self, "equals", None)
                if callable(equals_method_v_self):
                    if not equals_method_v_self(v_other):
                        return False
                elif v_self != v_other:
                    return False  # Fallback
            return True
        return False

    def __hash__(self):
        if isinstance(self._internal_collection, set):
            current_hash = 0
            for item in self._internal_collection:
                item_hash = 0
                if hasattr(item, "hashCode") and callable(item.hashCode):
                    item_hash = item.hashCode()
                elif item is not None:
                    try:
                        item_hash = hash(item)
                    except TypeError:
                        item_hash = id(item)
                current_hash += item_hash
            return current_hash
        elif isinstance(self._internal_collection, list):
            current_hash = 1
            for item in self._internal_collection:
                item_hash = 0
                if hasattr(item, "hashCode") and callable(item.hashCode):
                    item_hash = item.hashCode()
                elif item is not None:
                    try:
                        item_hash = hash(item)
                    except TypeError:
                        item_hash = id(item)
                current_hash = 31 * current_hash + item_hash
            return current_hash
        elif isinstance(self._internal_collection, dict):  # Map hashCode
            current_hash = 0
            for k, v in self._internal_collection.items():
                key_hash = 0
                if hasattr(k, "hashCode") and callable(k.hashCode):
                    key_hash = k.hashCode()
                elif k is not None:
                    try:
                        key_hash = hash(k)
                    except TypeError:
                        key_hash = id(k)

                value_hash = 0
                if hasattr(v, "hashCode") and callable(v.hashCode):
                    value_hash = v.hashCode()
                elif v is not None:
                    try:
                        value_hash = hash(v)
                    except TypeError:
                        value_hash = id(v)

                current_hash += key_hash ^ value_hash
            return current_hash

        try:  # Fallback générique
            if isinstance(self._internal_collection, set):
                return hash((self.class_name, frozenset(self._internal_collection)))
            else:  # list or dict (dict keys must be hashable for tuple)
                return hash(
                    (
                        self.class_name,
                        tuple(
                            self._internal_collection.items()
                            if isinstance(self._internal_collection, dict)
                            else self._internal_collection
                        ),
                    )
                )
        except TypeError:
            return hash(self.class_name)

    def __eq__(self, other):
        return self.equals(other)


class JObject:
    """Simule jpype.JObject."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._actual_value = None
        self._java_type_name = None

        if len(args) == 2:
            self._actual_value = args[0]
            java_type_arg = args[1]
            if hasattr(java_type_arg, "class_name"):
                self._java_type_name = java_type_arg.class_name
            elif isinstance(java_type_arg, str):
                self._java_type_name = java_type_arg
            pass

    def doubleValue(self):
        if self._java_type_name == "java.lang.Double":
            return float(self._actual_value)
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'doubleValue'"
        )

    def intValue(self):
        if self._java_type_name == "java.lang.Integer":
            return int(self._actual_value)
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'intValue'"
        )

    def booleanValue(self):
        if self._java_type_name == "java.lang.Boolean":
            return bool(self._actual_value)
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'booleanValue'"
        )

    def longValue(self):
        if self._java_type_name == "java.lang.Long":
            return int(self._actual_value)
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'longValue'"
        )

    def floatValue(self):
        if self._java_type_name == "java.lang.Float":
            return float(self._actual_value)
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'floatValue'"
        )

    def shortValue(self):
        if self._java_type_name == "java.lang.Short":
            return int(self._actual_value)
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'shortValue'"
        )

    def byteValue(self):
        if self._java_type_name == "java.lang.Byte":
            return int(self._actual_value)
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'byteValue'"
        )

    def charValue(self):
        if self._java_type_name == "java.lang.Character":
            char_val = str(self._actual_value)
            return char_val
        raise AttributeError(
            f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'charValue'"
        )


def JString(value):
    """Simule jpype.JString()."""
    jstring_mock = MagicMock(name=f"MockJString_{str(value)[:20]}")
    jstring_mock._mock_jpype_jstring_value = str(value)
    jstring_mock.toString = MagicMock(return_value=str(value))
    jstring_mock.__str__ = lambda s_self: str(
        value
    )  # s_self pour éviter conflit avec value externe
    jstring_mock.__repr__ = lambda s_self: f"JString('{str(value)}')"
    jstring_mock.__eq__ = MagicMock(
        side_effect=lambda other: str(value) == other
        if isinstance(other, str)
        else (
            hasattr(other, "_mock_jpype_jstring_value")
            and str(value) == other._mock_jpype_jstring_value
        )
        if isinstance(other, MagicMock)
        else False
    )
    jstring_mock.__hash__ = MagicMock(side_effect=lambda: hash(str(value)))
    # Simuler le fait que c'est une instance de java.lang.String
    jstring_mock.getClass = MagicMock(return_value=JClass("java.lang.String"))
    return jstring_mock


def JArray(type_):  # type_ est la classe des éléments
    """Simule jpype.JArray()."""
    array_mock = MagicMock(
        name=f"MockJArray_of_{type_.__name__ if hasattr(type_, '__name__') else str(type_)}"
    )
    array_mock._mock_jpype_array_elements = []

    def array_add(element):
        array_mock._mock_jpype_array_elements.append(element)
        return True

    def array_len():
        return len(array_mock._mock_jpype_array_elements)

    def array_iter():
        return iter(array_mock._mock_jpype_array_elements)

    def array_getitem(index):
        return array_mock._mock_jpype_array_elements[index]

    array_mock.add = MagicMock(side_effect=array_add)
    array_mock.__len__ = MagicMock(side_effect=array_len)
    array_mock.__iter__ = MagicMock(side_effect=array_iter)
    array_mock.__getitem__ = MagicMock(side_effect=array_getitem)
    # Simuler le type de l'array
    array_mock.getClass = MagicMock(
        return_value=JClass(
            f"Array<{type_.__name__ if hasattr(type_, '__name__') else str(type_)}>"
        )
    )
    return array_mock


def JBoolean(value):
    """Simule jpype.JBoolean()."""
    return JObject(value, JClass("java.lang.Boolean"))


def JInt(value):
    """Simule jpype.JInt()."""
    return JObject(value, JClass("java.lang.Integer"))


def JDouble(value):
    """Simule jpype.JDouble()."""
    return JObject(value, JClass("java.lang.Double"))


# Fonctions pour les autres types primitifs, utilisant JObject
def JLong(value):
    return JObject(value, JClass("java.lang.Long"))


def JFloat(value):
    return JObject(value, JClass("java.lang.Float"))


def JShort(value):
    return JObject(value, JClass("java.lang.Short"))


def JByte(value):
    return JObject(value, JClass("java.lang.Byte"))


def JChar(value):
    return JObject(value, JClass("java.lang.Character"))


mock_logger.info("Module jpype_components.types initialisé.")
