import logging
import sys
from unittest.mock import MagicMock
from .jclass_core import MockJClassCore

# Configuration du logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE TWEETY_ENUMS LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MockJavaEnumInstance(MagicMock):
    """
    Représente une instance spécifique d'une énumération Java mockée (par exemple, TruthValue.TRUE).
    Elle doit avoir des méthodes comme name() et ordinal().
    """
    def __init__(self, enum_class_name=None, enum_name=None, enum_ordinal=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if enum_class_name is None or enum_name is None or enum_ordinal is None:
            logger.warning(f"MockJavaEnumInstance initialisée sans arguments spécifiques (probablement par un mécanisme de mock interne). class_name: {enum_class_name}, name: {enum_name}, ordinal: {enum_ordinal}")
            self._enum_class_name = enum_class_name or "UnknownEnumClass"
            self._enum_name = enum_name or "UnknownEnumName"
            self._enum_ordinal = enum_ordinal if enum_ordinal is not None else -1
        else:
            self._enum_class_name = enum_class_name
            self._enum_name = enum_name
            self._enum_ordinal = enum_ordinal
        
        # Configurer les méthodes standard d'une enum Java
        # Utiliser des fonctions lambda pour capturer les valeurs actuelles de self._enum_name/ordinal
        self.name = MagicMock(side_effect=lambda: self._enum_name)
        self.ordinal = MagicMock(side_effect=lambda: self._enum_ordinal)

    def toString(self): # Rendre toString appelable
        return self._enum_name

    def equals(self, other):
        if not isinstance(other, MockJavaEnumInstance):
            return False
        return (self._enum_class_name == other._enum_class_name and
                self._enum_name == other._enum_name)

    def hashCode(self):
        return hash((self._enum_class_name, self._enum_name))

    def __eq__(self, other):
        return self.equals(other)

    def __hash__(self):
        return self.hashCode()

    # Python repr pour faciliter le débogage
    def __repr__(self):
        return f"<MockJavaEnumInstance {self._enum_class_name}.{self._enum_name}>"

    def _get_child_mock(self, **kwargs):
        """
        Surcharge pour s'assurer que les mocks enfants sont des MagicMock standard
        et n'essaient pas de réinstancier MockJavaEnumInstance sans les arguments requis.
        """
        return MagicMock(**kwargs)

class MockEnumMetaclass(type(MockJClassCore)):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls._enum_members = {} # Initialisé ici pour chaque classe d'enum

        # Ne pas appeler _initialize_enum_members pour la classe de base MockTweetyEnum elle-même,
        # seulement pour ses sous-classes concrètes.
        if hasattr(cls, '_initialize_enum_members') and cls.__name__ != "MockTweetyEnum":
            cls._initialize_enum_members()

        def values_method(klass):
            logger.debug(f"MockEnum {klass.__name__}.values() appelée. Membres: {list(klass._enum_members.values())}")
            # Idéalement, cela devrait être un tableau Java mocké (JArray).
            # Pour l'instant, retourne une liste Python.
            # from .types import JArray # Attention aux imports circulaires
            return list(klass._enum_members.values())
        
        cls.values = classmethod(values_method)

        # Rendre les membres de l'enum accessibles via __getattr__ sur la classe
        # pour simuler EnumName.MEMBER
        # Note: setattr dans _add_member fait déjà cela.
        # Cette métaclasse assure que _enum_members est prêt et values() est défini.


class MockTweetyEnum(MockJClassCore, metaclass=MockEnumMetaclass):
    _enum_members = {} # Sera peuplé par _add_member via _initialize_enum_members

    def __init__(self, name, jclass_provider_func=None):
        # L'appel à JClass("EnumName") doit retourner la CLASSE, pas une instance de celle-ci.
        # Donc, cet __init__ ne devrait normalement pas être appelé pour obtenir la classe Enum.
        # MockJClassCore.__init__ sera appelé par la métaclasse lors de la définition de la classe.
        super().__init__(name, jclass_provider_func)
        logger.debug(f"MockTweetyEnum (classe {self.__name__}) initialisée pour le nom Java {name}.")


    @classmethod
    def _initialize_enum_members(cls):
        # Les sous-classes doivent surcharger cette méthode.
        # Si cette méthode est appelée sur MockTweetyEnum elle-même, c'est une erreur de logique.
        if cls.__name__ == "MockTweetyEnum":
             logger.warning("MockTweetyEnum._initialize_enum_members appelée directement sur la classe de base. Cela ne devrait pas arriver.")
             return
        raise NotImplementedError(f"{cls.__name__} doit implémenter _initialize_enum_members.")

    @classmethod
    def _add_member(cls, name, ordinal):
        # Assurer que _enum_members est spécifique à la classe et non partagé via héritage simple
        if '_enum_members' not in cls.__dict__:
            cls._enum_members = {}

        if name in cls._enum_members:
            # Peut arriver si _initialize_enum_members est appelé plusieurs fois ou mal géré
            logger.warning(f"Tentative de redéfinition du membre d'enum {name} pour {cls.__name__}. Ignoré.")
            return cls._enum_members[name]
            
        java_class_name = getattr(cls, 'MOCK_JAVA_CLASS_NAME', cls.__name__)
        
        instance = MockJavaEnumInstance(enum_class_name=java_class_name, enum_name=name, enum_ordinal=ordinal)
        cls._enum_members[name] = instance
        setattr(cls, name, instance) 
        logger.debug(f"Membre d'enum ajouté à {cls.__name__} ({java_class_name}): {name} (ordinal {ordinal}) -> {instance}")
        return instance

    @classmethod
    def valueOf(cls, name_str):
        logger.debug(f"MockEnum {cls.__name__}.valueOf('{name_str}') appelée. Membres: {list(cls._enum_members.keys())}")
        
        actual_string = str(name_str) if not isinstance(name_str, str) else name_str

        if actual_string in cls._enum_members:
            return cls._enum_members[actual_string]
        else:
            java_class_name = getattr(cls, 'MOCK_JAVA_CLASS_NAME', cls.__name__)
            logger.error(f"Aucun membre d'enum avec le nom '{actual_string}' trouvé dans {java_class_name}. Membres: {list(cls._enum_members.keys())}")
            # Simuler java.lang.IllegalArgumentException
            # Pour l'instant, une ValueError Python. Si JException est disponible et configuré:
            # from .exceptions import JException
            # raise JException(f"No enum constant {java_class_name}.{actual_string}")
            raise ValueError(f"No enum constant {java_class_name}.{actual_string}")

    # Surcharger __call__ pour empêcher l'instanciation EnumName()
    # JClass("EnumName") retourne la classe. EnumName() n'est pas valide en Java.
    def __call__(self, *args, **kwargs):
        raise TypeError(f"Les classes Enum Java ne peuvent pas être instanciées directement. Utilisez les membres statiques (ex: {self.__name__}.MEMBER_NAME).")

# --- Définitions des énumérations spécifiques ---

class TruthValue(MockTweetyEnum):
    MOCK_JAVA_CLASS_NAME = "org.tweetyproject.commons.util.TruthValue"

    @classmethod
    def _initialize_enum_members(cls):
        cls.TRUE = cls._add_member("TRUE", 0)
        cls.FALSE = cls._add_member("FALSE", 1)
        cls.UNKNOWN = cls._add_member("UNKNOWN", 2)
        cls.INCONSISTENT = cls._add_member("INCONSISTENT", 3)

class ComparisonMethod(MockTweetyEnum):
    MOCK_JAVA_CLASS_NAME = "org.tweetyproject.commons.util.ComparisonMethod"

    @classmethod
    def _initialize_enum_members(cls):
        cls.EQUALS = cls._add_member("EQUALS", 0)
        cls.NOT_EQUALS = cls._add_member("NOT_EQUALS", 1)
        cls.LESS_THAN = cls._add_member("LESS_THAN", 2)
        cls.LESS_THAN_OR_EQUALS = cls._add_member("LESS_THAN_OR_EQUALS", 3)
        cls.GREATER_THAN = cls._add_member("GREATER_THAN", 4)
        cls.GREATER_THAN_OR_EQUALS = cls._add_member("GREATER_THAN_OR_EQUALS", 5)

class SuccessFailure(MockTweetyEnum):
    MOCK_JAVA_CLASS_NAME = "org.tweetyproject.commons.util.SuccessFailure"

    @classmethod
    def _initialize_enum_members(cls):
        cls.SUCCESS = cls._add_member("SUCCESS", 0)
        cls.FAILURE = cls._add_member("FAILURE", 1)

# Dictionnaire pour mapper les noms de classes Java aux classes mockées d'énumération
ENUM_MAPPINGS = {
    TruthValue.MOCK_JAVA_CLASS_NAME: TruthValue,
    ComparisonMethod.MOCK_JAVA_CLASS_NAME: ComparisonMethod,
    SuccessFailure.MOCK_JAVA_CLASS_NAME: SuccessFailure,
}

logger.info("Module jpype_components.tweety_enums initialisé avec les mocks d'énumérations Tweety.")