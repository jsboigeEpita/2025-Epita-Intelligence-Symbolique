from unittest.mock import MagicMock
import logging
import sys
from itertools import chain, combinations # Pour les helpers de sémantique d'argumentation
from . import tweety_reasoners # Ajout pour les configurations de reasoners
from . import tweety_agents # Ajout pour les configurations des agents

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE JCLASS_CORE LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

# Dépendances qui seront dans d'autres fichiers de jpype_components
# from .types import JString, JArray, JObject # etc. - Pour l'instant, on évite l'import direct pour prévenir les cycles

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
            raise StopIteration("No more elements in mock Java iterator")
        current_item = self._next_item
        self._advance()
        return current_item

class MockJavaCollection:
    def __init__(self, java_class_name, *constructor_args):
        self.class_name = java_class_name
        self._constructor_args = constructor_args
        self._internal_collection = self._determine_internal_collection_type()
        mock_logger.debug(f"MockJavaCollection '{self.class_name}' créée. Args: {constructor_args}")

        if constructor_args:
            initial_data = constructor_args[0]
            if hasattr(initial_data, '__iter__'):
                try:
                    # Si initial_data est un mock avec une méthode iterator() (comme un autre MockJavaCollection)
                    if hasattr(initial_data, 'iterator') and callable(initial_data.iterator):
                        it = initial_data.iterator()
                        while it.hasNext():
                            self.add(it.next())
                    else: # Fallback pour les itérables Python simples
                        for item in initial_data:
                            self.add(item)
                except TypeError:
                    mock_logger.warning(f"MockJavaCollection pour {self.class_name} a reçu un argument de constructeur non itérable: {initial_data}")
            elif initial_data is not None:
                 mock_logger.warning(f"MockJavaCollection pour {self.class_name} a reçu un argument de constructeur non-collection: {initial_data}")


    def _determine_internal_collection_type(self):
        if "Set" in self.class_name or "HashSet" in self.class_name:
            return set()
        return []

    def add(self, element):
        if isinstance(self._internal_collection, list):
            self._internal_collection.append(element)
            return True
        elif isinstance(self._internal_collection, set):
            is_new = element not in self._internal_collection
            self._internal_collection.add(element)
            return is_new
        return False

    def size(self):
        s = len(self._internal_collection)
        mock_logger.debug(f"MockJavaCollection '{self.class_name}'.size() -> {s}. Contenu: {self._internal_collection}")
        return s
        
    def isEmpty(self):
        return len(self._internal_collection) == 0

    def contains(self, element):
        # Logique de comparaison améliorée
        if hasattr(element, 'equals') and callable(element.equals):
            for item in self._internal_collection:
                if element.equals(item):
                    return True
            return False
        # Fallback pour les éléments non mockés ou sans .equals()
        return element in self._internal_collection


    def remove(self, element):
        try:
            if isinstance(self._internal_collection, list):
                # Pour les listes, l'égalité des éléments doit être gérée avec .equals si possible
                item_to_remove = None
                for item in self._internal_collection:
                    if hasattr(element, 'equals') and callable(element.equals):
                        if element.equals(item):
                            item_to_remove = item
                            break
                    elif element == item: # Fallback
                        item_to_remove = item
                        break
                if item_to_remove is not None:
                    self._internal_collection.remove(item_to_remove)
                    return True
                return False
            elif isinstance(self._internal_collection, set):
                # Pour les sets, la gestion de .equals est implicite si les objets sont correctement hashables
                # et que .equals est cohérent avec __hash__.
                # Si element est dans la collection (basé sur __hash__ et __eq__), remove fonctionnera.
                if element in self._internal_collection: # Utilise __eq__ et __hash__ de l'élément
                    self._internal_collection.remove(element)
                    return True
                return False
        except ValueError:
            return False
        return False

    def clear(self):
        self._internal_collection.clear()

    def __iter__(self):
        return iter(self._internal_collection)

    def toString(self):
        return str(list(self._internal_collection))

    def equals(self, other):
        if not isinstance(other, MockJavaCollection) or self.class_name != other.class_name:
            return False
        if self.size() != other.size():
            return False
        
        if isinstance(self._internal_collection, list):
            # Comparaison ordonnée, élément par élément avec .equals()
            for item_self, item_other in zip(self, other): # Utilise __iter__
                equals_method_self = getattr(item_self, "equals", None)
                if callable(equals_method_self):
                    if not equals_method_self(item_other):
                        return False
                elif item_self != item_other: # Fallback
                    return False
            return True
        elif isinstance(self._internal_collection, set):
            # Comparaison non ordonnée. Vérifier si tous les éléments de self sont dans other
            # et vice-versa, en utilisant .contains() qui devrait utiliser .equals().
            # Ceci suppose que les éléments ont une méthode .equals() et __hash__() cohérente.
            if len(self._internal_collection) != len(other._internal_collection): # Redondant avec size() check mais ok
                return False
            for item_s in self._internal_collection:
                if not other.contains(item_s): # Utilise other.contains qui devrait utiliser .equals
                    return False
            return True
        return False

    def iterator(self):
        return _ModuleLevelMockJavaIterator(self._internal_collection)

    def __hash__(self):
        # Un hash simple basé sur le nom de la classe et le contenu.
        # Pour que les MockJavaCollection puissent être dans des sets si nécessaire.
        # Les éléments de _internal_collection doivent être hashables.
        # Si _internal_collection est une liste, l'ordre compte. Si c'est un set, non.
        if isinstance(self._internal_collection, set):
            # Pour un set, le hash doit être indépendant de l'ordre.
            # On peut trier les hash des éléments (si possible) ou utiliser frozenset.
            try:
                return hash((self.class_name, frozenset(self._internal_collection)))
            except TypeError: # Si les éléments ne sont pas hashables
                return hash(self.class_name) # Fallback
        else: # Pour une liste
            try:
                return hash((self.class_name, tuple(self._internal_collection)))
            except TypeError:
                return hash(self.class_name) # Fallback

    def __eq__(self, other):
        return self.equals(other)


class MockJClassCore:
    def __init__(self, name, jclass_provider_func=None):
        self.__name__ = name # Nom qualifié de la classe Java, ex: "java.lang.String"
        self.class_name = name
        self._static_attributes = {}
        self._instance_specific_config = {} # Pour stocker des configs spécifiques à une classe
        self._jclass_provider = jclass_provider_func # Pour que les configurateurs puissent créer des JClass
        mock_logger.debug(f"MockJClassCore pour '{name}' initialisée (jclass_provider: {jclass_provider_func is not None}).")

        # Logique de base pour java.lang.ClassLoader.getSystemClassLoader()
        if self.class_name == "java.lang.ClassLoader":
            def mock_get_system_class_loader():
                mock_logger.info(f"[MOCK] java.lang.ClassLoader.getSystemClassLoader() CALLED")
                # Retourne un mock de ClassLoader. Pour l'instant, une nouvelle instance de MockJClassCore.
                # Si des méthodes spécifiques sont appelées sur le loader retourné (ex: loadClass),
                # elles devront être mockées sur cette instance retournée.
                # Par exemple: loader_mock.loadClass = MagicMock(side_effect=lambda name: MockJClassCore(name))
                # Pour l'instant, on retourne une instance simple.
                # Le JClass() global sera utilisé par le code appelant pour créer cette instance.
                # Ici, on retourne directement une instance de MockJClassCore pour simuler le ClassLoader.
                # Cela évite une dépendance circulaire à un JClass() global dans ce module.
                return MockJClassCore('java.lang.ClassLoader') # Simule un objet ClassLoader
            self._static_attributes['getSystemClassLoader'] = mock_get_system_class_loader
            mock_logger.debug(f"Méthode statique 'getSystemClassLoader' configurée pour java.lang.ClassLoader.")

    def __getattr__(self, attr_name):
        mock_logger.debug(f"MockJClassCore('{self.class_name}').__getattr__('{attr_name}')")
        if attr_name in self._static_attributes:
            return self._static_attributes[attr_name]
        
        # Comportement par défaut si l'attribut n'est pas un attribut statique défini.
        # JPype lève une AttributeError pour les champs statiques non trouvés.
        # Si c'est une méthode statique non définie, cela lèverait aussi une erreur.
        # Pour simuler cela, on lève AttributeError.
        # Si on voulait simuler des classes internes statiques, la logique serait ici.
        # Ex: if attr_name == "MyInnerStaticClass": return MockJClassCore(f"{self.class_name}${attr_name}")
        raise AttributeError(f"MockJClassCore '{self.class_name}' has no static attribute '{attr_name}' or it's not defined in _static_attributes.")

    def __call__(self, *args, **kwargs):
        mock_logger.debug(f"MockJClassCore('{self.class_name}').__call__ avec args: {args}, kwargs: {kwargs}")

        # Gestion spécifique pour les collections java.util.*
        # Si on instancie une classe de java.util (ex: HashSet()), on retourne un MockJavaCollection.
        if self.class_name.startswith("java.util.") and \
           ("List" in self.class_name or \
            "Set" in self.class_name or \
            "Map" in self.class_name or \
            "Collection" in self.class_name or \
            "Queue" in self.class_name or \
            "Deque" in self.class_name):
            mock_logger.info(f"Instanciation d'une collection Java simulée: {self.class_name}")
            return MockJavaCollection(self.class_name, *args) # args sont passés au constructeur de MockJavaCollection

        # Comportement par défaut: retourner un MagicMock pour simuler une instance d'objet Java.
        # Ce MagicMock aura le class_name de l'objet qu'il simule.
        instance_mock = MagicMock(name=f"MockInstanceOf_{self.class_name}")
        instance_mock.class_name = self.class_name 
        instance_mock._constructor_args = args # Stocker les args pour .equals() et .hashCode()
        instance_mock._kwargs_constructor = kwargs # Stocker les kwargs aussi
        instance_mock._collections = {} # Pour les classes qui gèrent des collections internes (ex: DungTheory)
        instance_mock._attributes = {}  # Pour les attributs simples (ex: maxTurns)

        # Configurer .toString() par défaut
        instance_mock.toString = MagicMock(return_value=f"MockedToString_{self.class_name}({args}, {kwargs})")

        # Configurer .equals() et .hashCode() par défaut pour l'instance mockée
        # Ces méthodes sont cruciales pour le comportement dans les collections et les comparaisons.
        
        def default_instance_equals(other_obj):
            mock_logger.debug(f"[DEFAULT_INSTANCE_EQUALS] pour {instance_mock.class_name} ({id(instance_mock)}) vs {getattr(other_obj, 'class_name', 'N/A')} ({id(other_obj)})")
            if not isinstance(other_obj, MagicMock) or \
               not hasattr(other_obj, 'class_name') or \
               instance_mock.class_name != other_obj.class_name:
                mock_logger.debug(f"  -> Types différents ou other_obj n'est pas un mock attendu. Retour False.")
                return False
            
            # Comparaison basée sur les arguments du constructeur
            # (simpliste, mais un point de départ)
            # Doit vérifier que _constructor_args existe sur les deux.
            self_args = getattr(instance_mock, '_constructor_args', None)
            other_args = getattr(other_obj, '_constructor_args', None)

            if self_args is None or other_args is None:
                # Si l'un n'a pas _constructor_args, on ne peut pas comparer ainsi.
                # On pourrait considérer qu'ils ne sont égaux que s'ils sont le même objet.
                # Ou si les deux n'ont pas d'args et sont du même type.
                # Pour l'instant, si l'un manque d'args, on dit False sauf si les deux manquent d'args.
                is_equal = (self_args is None and other_args is None)
                mock_logger.debug(f"  -> L'un ou les deux manquent _constructor_args. Égalité: {is_equal}. Retour {is_equal}.")
                return is_equal

            if len(self_args) != len(other_args):
                mock_logger.debug(f"  -> Longueurs d'args différentes. Retour False.")
                return False
            
            for i in range(len(self_args)):
                arg_self = self_args[i]
                arg_other = other_args[i]
                
                # Si les arguments sont eux-mêmes des mocks avec .equals()
                if hasattr(arg_self, 'equals') and callable(arg_self.equals):
                    if not arg_self.equals(arg_other):
                        mock_logger.debug(f"  -> arg_self[{i}].equals(arg_other[{i}]) a retourné False.")
                        return False
                elif arg_self != arg_other: # Comparaison Python standard
                    mock_logger.debug(f"  -> arg_self[{i}] != arg_other[{i}] (Python standard) a retourné False.")
                    return False
            mock_logger.debug(f"  -> Tous les args sont égaux. Retour True.")
            return True

        instance_mock.equals = MagicMock(name=f"{self.class_name}_equals", side_effect=default_instance_equals)

        def default_instance_hash_code():
            # Hash basé sur class_name et les hash des arguments du constructeur.
            # Nécessite que les arguments soient hashables.
            # Si les args sont des mocks, ils devraient avoir leur propre .hashCode().
            args_to_hash = []
            if hasattr(instance_mock, '_constructor_args'):
                for arg_val in instance_mock._constructor_args:
                    if hasattr(arg_val, 'hashCode') and callable(arg_val.hashCode):
                        args_to_hash.append(arg_val.hashCode())
                    elif isinstance(arg_val, MagicMock): # Mock sans .hashCode() explicite
                        args_to_hash.append(object.__hash__(arg_val))
                    else:
                        try:
                            args_to_hash.append(hash(arg_val))
                        except TypeError:
                             # Si un arg n'est pas hashable, on utilise son id ou une constante
                            args_to_hash.append(id(arg_val)) 
            
            h = hash((instance_mock.class_name, tuple(args_to_hash)))
            mock_logger.debug(f"[DEFAULT_INSTANCE_HASH_CODE] pour {instance_mock.class_name} ({id(instance_mock)}). Args: {args_to_hash}. Hash: {h}")
            return h

        instance_mock.hashCode = MagicMock(name=f"{self.class_name}_hashCode", side_effect=default_instance_hash_code)

        # Pour compatibilité avec les sets/dicts Python, __eq__ et __hash__ sur le mock lui-même.
        instance_mock.__eq__ = MagicMock(side_effect=lambda other: instance_mock.equals(other) if hasattr(instance_mock, 'equals') else NotImplemented)
        instance_mock.__hash__ = MagicMock(side_effect=lambda: instance_mock.hashCode() if hasattr(instance_mock, 'hashCode') else object.__hash__(instance_mock))

        # Appliquer des configurations spécifiques à l'instance si elles existent
        # (sera rempli par d'autres modules comme tweety_syntax.py, etc.)
        # Par exemple, si self.class_name est "org.tweetyproject.arg.dung.syntax.Argument",
        # le module tweety_syntax.py pourrait avoir une fonction qui prend instance_mock
        # et configure .getName(), .equals(), .hashCode() spécifiquement pour Argument.
        # Cette logique de "patching" sera dans le jpype_mock.py principal ou dans les modules tweety_*.

        # --- Configuration spécifique pour les Reasoners ---
        # Les reasoners prennent souvent une DungTheory en argument constructeur
        dung_theory_instance_arg = args[0] if args else None

        if self._jclass_provider is None:
            mock_logger.warning(f"JClass provider non disponible pour MockJClassCore('{self.class_name}'), la configuration des reasoners pourrait être limitée.")
        
        if self.class_name == "net.sf.tweety.arg.dung.reasoner.CompleteReasoner":
            if self._jclass_provider:
                tweety_reasoners.configure_complete_reasoner_mock(instance_mock, dung_theory_instance_arg, self._jclass_provider)
            else:
                mock_logger.error("Impossible de configurer CompleteReasoner: JClass provider manquant.")
        elif self.class_name == "net.sf.tweety.arg.dung.reasoner.StableReasoner":
            if self._jclass_provider:
                tweety_reasoners.configure_stable_reasoner_mock(instance_mock, dung_theory_instance_arg, self._jclass_provider)
            else:
                mock_logger.error("Impossible de configurer StableReasoner: JClass provider manquant.")
        elif self.class_name == "net.sf.tweety.arg.dung.reasoner.PreferredReasoner":
            if self._jclass_provider:
                tweety_reasoners.configure_preferred_reasoner_mock(instance_mock, dung_theory_instance_arg, self._jclass_provider)
            else:
                mock_logger.error("Impossible de configurer PreferredReasoner: JClass provider manquant.")
        elif self.class_name == "net.sf.tweety.arg.dung.reasoner.GroundedReasoner":
            if self._jclass_provider:
                tweety_reasoners.configure_grounded_reasoner_mock(instance_mock, dung_theory_instance_arg, self._jclass_provider)
            else:
                mock_logger.error("Impossible de configurer GroundedReasoner: JClass provider manquant.")
        # --- Fin de la configuration des Reasoners ---

        # --- Configuration spécifique pour les Agents Tweety ---
        if self.class_name.startswith("org.tweetyproject.agents."):
            if self._jclass_provider: # Le configurateur d'agent pourrait en avoir besoin
                mock_logger.debug(f"Appel de la configuration spécifique pour la classe d'agent: {self.class_name}")
                tweety_agents.configure_tweety_agent_class(instance_mock)
            else:
                mock_logger.warning(f"JClass provider non disponible pour MockJClassCore('{self.class_name}'), la configuration des agents pourrait être limitée.")
        # --- Fin de la configuration des Agents Tweety ---

        mock_logger.info(f"Instance mockée de '{self.class_name}' créée et retournée.")
        return instance_mock

    def equals(self, other_obj):
        """Comparaison pour l'objet MockJClassCore lui-même (la classe, pas l'instance)."""
        if not isinstance(other_obj, MockJClassCore):
            return False
        return self.class_name == other_obj.class_name

    def hashCode(self):
        """Hash pour l'objet MockJClassCore lui-même."""
        return hash(self.class_name)

    def __eq__(self, other):
        return self.equals(other)

    def __hash__(self):
        return self.hashCode()


mock_logger.info("Module jpype_components.jclass_core initialisé.")