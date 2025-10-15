from unittest.mock import MagicMock

# --- Mock de base ---
# Remplacer create_autospec par MagicMock pour permettre l'assignation dynamique d'attributs.
# Pour que le mock soit considéré comme un package, il doit avoir un __path__
jpype_mock = MagicMock(name="jpype_mock_package")
jpype_mock.__path__ = ["/mock/path/jpype"]


# --- Partie 1 : Mocker les types pour isinstance() ---
class MockJType:
    def __init__(self, target_type, name):
        self._target_type = target_type
        self.__name__ = name  # Pour un meilleur débogage

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


# --- Partie 2 : Mocker JClass (factory de classes Java) ---
def mock_JClass(class_name):
    """Mock de JClass qui crée des classes Java simulées.
    
    Args:
        class_name: Nom complet de la classe Java (ex: 'java.lang.String')
    
    Returns:
        Une classe mock avec attributs Java-like
    """
    mock_class = MagicMock(name=f"MockJavaClass_{class_name}")
    mock_class.class_name = class_name
    mock_class.__name__ = class_name.split('.')[-1]
    
    # Simuler le constructeur de classe
    def mock_constructor(*args, **kwargs):
        instance = MagicMock(name=f"Instance_{class_name}")
        instance._class = mock_class
        instance._value = args[0] if args else None
        return instance
    
    mock_class.__call__ = mock_constructor
    return mock_class


jpype_mock.JClass = mock_JClass


# --- Partie 3 : Mocker JException (exception Java complète) ---
class MockJException(Exception):
    """Mock de JException avec interface Java-like."""
    
    def __init__(self, message=""):
        super().__init__(message)
        self.message = message
        self._java_class = MagicMock(name="JavaClass_MockException")
        self._java_class.getName.return_value = "org.mockexception.MockException"
    
    def getClass(self):
        """Simule la méthode getClass() de Java."""
        return self._java_class
    
    def getMessage(self):
        """Simule la méthode getMessage() de Java."""
        return self.message


jpype_mock.JException = MockJException


# --- Partie 4 : Mocker les attributs manquants ---
jpype_mock.java = MagicMock()
jpype_mock.JPackage = MagicMock()
# Ajout pour résoudre l'erreur dans les tests e2e
jpype_mock.imports = MagicMock()


# --- Partie 3 : Mocker l'exception JVMNotStarted ---
jpype_mock._core = MagicMock()
jpype_mock._core.JVMNotStarted = type("JVMNotStarted", (Exception,), {})

# --- Fonctions de base ---
# Maintenant, ces assignations devraient fonctionner car jpype_mock est un MagicMock standard.
jpype_mock.isJVMStarted.return_value = False
jpype_mock.startJVM.return_value = None
jpype_mock.shutdownJVM.return_value = None
jpype_mock.addClassPath.return_value = None

# Exporter le mock principal pour qu'il soit utilisé par le bootstrap
__all__ = ["jpype_mock"]
