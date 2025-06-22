from unittest.mock import MagicMock

# --- Mock de base ---
# Remplacer create_autospec par MagicMock pour permettre l'assignation dynamique d'attributs.
# Pour que le mock soit considéré comme un package, il doit avoir un __path__
jpype_mock = MagicMock(name='jpype_mock_package')
jpype_mock.__path__ = ['/mock/path/jpype']

# --- Partie 1 : Mocker les types pour isinstance() ---
class MockJType:
    def __init__(self, target_type, name):
        self._target_type = target_type
        self.__name__ = name # Pour un meilleur débogage

    def __instancecheck__(self, instance):
        if self._target_type == list:
            return isinstance(instance, list)
        return isinstance(instance, self._target_type)

    def __call__(self, value, *args, **kwargs):
        if self._target_type == list:
            if isinstance(value, list):
                return value
            else:
                return lambda x: list(x)
        return self._target_type(value)

# Assigner les mocks de type
jpype_mock.JInt = MockJType(int, "JInt")
jpype_mock.JFloat = MockJType(float, "JFloat")
jpype_mock.JBoolean = MockJType(bool, "JBoolean")
jpype_mock.JString = MockJType(str, "JString")
jpype_mock.JArray = MockJType(list, "JArray")


# --- Partie 2 : Mocker les attributs manquants ---
jpype_mock.JException = type('JException', (Exception,), {})
jpype_mock.java = MagicMock()
jpype_mock.JPackage = MagicMock()
# Ajout pour résoudre l'erreur dans les tests e2e
jpype_mock.imports = MagicMock()


# --- Partie 3 : Mocker l'exception JVMNotStarted ---
jpype_mock._core = MagicMock()
jpype_mock._core.JVMNotStarted = type('JVMNotStarted', (Exception,), {})

# --- Fonctions de base ---
# Maintenant, ces assignations devraient fonctionner car jpype_mock est un MagicMock standard.
jpype_mock.isJVMStarted.return_value = False
jpype_mock.startJVM.return_value = None
jpype_mock.shutdownJVM.return_value = None
jpype_mock.addClassPath.return_value = None

# Exporter le mock principal pour qu'il soit utilisé par le bootstrap
__all__ = ['jpype_mock']
