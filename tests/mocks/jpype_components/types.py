from unittest.mock import MagicMock
import logging
import sys

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE TYPES LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

from .jclass_core import MockJClassCore

# Remplacer l'utilisation du placeholder par la vraie classe MockJClassCore
# Nous utiliserons un alias JClass pour la lisibilité et la compatibilité sémantique.
JClass = MockJClassCore

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
            if hasattr(java_type_arg, 'class_name'):
                self._java_type_name = java_type_arg.class_name
            elif isinstance(java_type_arg, str):
                self._java_type_name = java_type_arg
            # elif isinstance(java_type_arg, MagicMock) and java_type_arg.name == "JClass_placeholder_for_types_module": # Gérer le placeholder
            #      # On ne peut pas vraiment obtenir un class_name du placeholder,
            #      # mais on peut le marquer pour indiquer que le type est "inconnu à cause du placeholder"
            #      self._java_type_name = "unknown_due_to_JClass_placeholder"
            # Après le remplacement du placeholder, java_type_arg devrait être une instance de MockJClassCore
            # et donc hasattr(java_type_arg, 'class_name') devrait être vrai.
            # La condition précédente `if hasattr(java_type_arg, 'class_name'):` devrait gérer cela.
            # On laisse le bloc commenté au cas où, mais il ne devrait plus être atteint.
            pass # La logique est maintenant couverte par hasattr(java_type_arg, 'class_name')


    def doubleValue(self):
        if self._java_type_name == "java.lang.Double":
            return float(self._actual_value)
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'doubleValue'")

    def intValue(self):
        if self._java_type_name == "java.lang.Integer":
            return int(self._actual_value)
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'intValue'")

    def booleanValue(self):
        if self._java_type_name == "java.lang.Boolean":
            return bool(self._actual_value)
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'booleanValue'")

    def longValue(self):
        if self._java_type_name == "java.lang.Long":
            return int(self._actual_value)
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'longValue'")

    def floatValue(self):
        if self._java_type_name == "java.lang.Float":
            return float(self._actual_value)
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'floatValue'")

    def shortValue(self):
        if self._java_type_name == "java.lang.Short":
            return int(self._actual_value)
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'shortValue'")

    def byteValue(self):
        if self._java_type_name == "java.lang.Byte":
            return int(self._actual_value)
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'byteValue'")

    def charValue(self):
        if self._java_type_name == "java.lang.Character":
            char_val = str(self._actual_value)
            return char_val
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'charValue'")

def JString(value):
    """Simule jpype.JString()."""
    jstring_mock = MagicMock(name=f"MockJString_{str(value)[:20]}")
    jstring_mock._mock_jpype_jstring_value = str(value)
    jstring_mock.toString = MagicMock(return_value=str(value))
    jstring_mock.__str__ = lambda s_self: str(value) # s_self pour éviter conflit avec value externe
    jstring_mock.__repr__ = lambda s_self: f"JString('{str(value)}')"
    jstring_mock.__eq__ = MagicMock(side_effect=lambda other: str(value) == other if isinstance(other, str) else \
                                     (hasattr(other, '_mock_jpype_jstring_value') and \
                                      str(value) == other._mock_jpype_jstring_value) if isinstance(other, MagicMock) else False)
    jstring_mock.__hash__ = MagicMock(side_effect=lambda: hash(str(value)))
    # Simuler le fait que c'est une instance de java.lang.String
    jstring_mock.getClass = MagicMock(return_value=JClass("java.lang.String"))
    return jstring_mock

def JArray(type_): # type_ est la classe des éléments
    """Simule jpype.JArray()."""
    array_mock = MagicMock(name=f"MockJArray_of_{type_.__name__ if hasattr(type_, '__name__') else str(type_)}")
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
    array_mock.getClass = MagicMock(return_value=JClass(f"Array<{type_.__name__ if hasattr(type_, '__name__') else str(type_)}>"))
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