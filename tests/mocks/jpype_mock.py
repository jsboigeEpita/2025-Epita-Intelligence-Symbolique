"""
Mock de JPype1 pour la compatibilité avec Python 3.12+.

Ce mock simule les fonctionnalités essentielles de JPype1 utilisées par le projet.
"""

import sys
import os
from unittest.mock import MagicMock
import logging

# Configuration du logging pour le mock lui-même
mock_logger = logging.getLogger(__name__)
# S'assurer que le logger a un handler pour afficher les messages, même si le projet principal
# configure le logging plus tard. Ceci est utile pour le débogage du mock lui-même.
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.INFO) # ou logging.DEBUG pour plus de verbosité

mock_logger.info("Module jpype_mock.py en cours de chargement.")

# Version du mock
__version__ = "1.4.0-mock"

# Variables globales pour simuler l'état de la JVM
_jvm_started = False
_jvm_path = None

# Simuler jpype.config
class MockConfig:
    def __init__(self):
        self.jvm_path = None # Initialement None, peut être défini par startJVM
        self.convertStrings = False # Valeur par défaut typique
        # Ajouter d'autres attributs de config si besoin
config = MockConfig()


# Simuler jpype.java (pour accès comme jpype.java.lang.String)
class MockJavaNamespace:
    def __init__(self, path_prefix=""):
        self._path_prefix = path_prefix

    def __getattr__(self, name):
        # Si on demande jpype.java.lang, on retourne un nouveau MockJavaNamespace pour 'lang'
        # Si on demande jpype.java.lang.String, on retourne JClass('java.lang.String')
        new_path = f"{self._path_prefix}.{name}" if self._path_prefix else name
        
        # Heuristique: si le nom commence par une majuscule, c'est probablement une classe.
        # Sinon, c'est un sous-package.
        # Ceci n'est pas parfait mais couvre de nombreux cas.
        # Ex: java.lang.String vs java.util.List
        # java.lang -> sous-package
        # java.lang.String -> classe
        
        # Pour éviter une récursion infinie avec des noms comme 'some.package.MyClass.MyInnerClass'
        # on pourrait avoir une liste de classes connues ou une logique plus fine.
        # Pour l'instant, si le dernier segment commence par une majuscule, on suppose que c'est une classe.
        final_segment = new_path.split('.')[-1]
        if final_segment and final_segment[0].isupper():
            mock_logger.debug(f"Accès à jpype.java...{new_path}, interprété comme JClass('{new_path}')")
            return JClass(new_path) # Retourne une instance de MockJClass
        else:
            mock_logger.debug(f"Accès à jpype.java...{new_path}, interprété comme sous-namespace")
            return MockJavaNamespace(new_path)

java = MockJavaNamespace("java") # Pour jpype.java.xxx
# On pourrait aussi avoir besoin de simuler d'autres packages de haut niveau comme 'org', 'net', etc.
# si le code fait jpype.org.tweetyproject...
# Pour l'instant, on se concentre sur 'java'.

def isJVMStarted():
    """Simule jpype.isJVMStarted()."""
    return _jvm_started

def startJVM(jvmpath=None, *args, **kwargs):
    """Simule jpype.startJVM()."""
    global _jvm_started, _jvm_path
    _jvm_started = True
    _jvm_path = jvmpath or getDefaultJVMPath()
    # Mettre à jour config.jvm_path aussi, car c'est souvent là que le code le cherche après démarrage
    config.jvm_path = _jvm_path
    mock_logger.info(f"JVM démarrée avec le chemin: {_jvm_path}")

def shutdownJVM():
    """Simule jpype.shutdownJVM()."""
    global _jvm_started
    print("[MOCK DEBUG] Avant opérations dans shutdownJVM:")
    jpype_module = sys.modules.get('jpype')
    print(f"[MOCK DEBUG] sys.modules.get('jpype'): {jpype_module}")
    print(f"[MOCK DEBUG] getattr(jpype_module, '__file__', 'N/A'): {getattr(jpype_module, '__file__', 'N/A')}")
    print(f"[MOCK DEBUG] hasattr(jpype_module, 'config'): {hasattr(jpype_module, 'config')}")
    has_core = hasattr(jpype_module, '_core')
    print(f"[MOCK DEBUG] hasattr(jpype_module, '_core'): {has_core}")
    if has_core and jpype_module._core is not None: # Vérifier aussi que _core n'est pas None
        print(f"[MOCK DEBUG] hasattr(jpype_module._core, '_JTerminate'): {hasattr(jpype_module._core, '_JTerminate')}")
    elif has_core and jpype_module._core is None:
        print(f"[MOCK DEBUG] jpype_module._core est None.")
    
    _jvm_started = False
    mock_logger.info("JVM arrêtée")

def getDefaultJVMPath():
    """Simule jpype.getDefaultJVMPath()."""
    # Retourner un chemin par défaut basé sur l'OS
    if sys.platform == "win32":
        return "C:\\Program Files\\Java\\jdk-11\\bin\\server\\jvm.dll"
    elif sys.platform == "darwin":
        return "/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home/lib/server/libjvm.dylib"
    else:
        return "/usr/lib/jvm/java-11-openjdk/lib/server/libjvm.so"

def getJVMPath():
    """Simule jpype.getJVMPath()."""
    return _jvm_path or getDefaultJVMPath()

def getJVMVersion():
    """Simule jpype.getJVMVersion()."""
    # Retourne un tuple similaire à celui de JPype: (version_string, major, minor, patch)
    return ("Mock JVM Version 1.0 (Java 11 compatible)", 11, 0, 0)

class MockJClass:
    """Mock pour JClass avec attributs spécifiques."""
    def __init__(self, name):
        self.__name__ = name
        self.class_name = name
        self._static_attributes = {}

        if name == "net.sf.tweety.arg.dung.semantics.OpponentModel":
            mock_simple = MagicMock(name="OpponentModel.SIMPLE_enum_instance")
            mock_simple.toString.return_value = "SIMPLE"
            mock_simple.name.return_value = "SIMPLE" # Souvent utilisé pour les enums Java
            # Idéalement, class_name ici serait le type de l'enum lui-même,
            # mais pour l'accès statique, cela pourrait ne pas être crucial.
            mock_simple.class_name = name
            self._static_attributes["SIMPLE"] = mock_simple

        if name == "org.tweetyproject.logics.qbf.syntax.Quantifier":
            mock_exists = MagicMock(name="Quantifier.EXISTS_enum_instance")
            mock_exists.toString.return_value = "EXISTS"
            mock_exists.name.return_value = "EXISTS"
            mock_exists.class_name = name
            self._static_attributes["EXISTS"] = mock_exists

            mock_forall = MagicMock(name="Quantifier.FORALL_enum_instance")
            mock_forall.toString.return_value = "FORALL"
            mock_forall.name.return_value = "FORALL"
            mock_forall.class_name = name
            self._static_attributes["FORALL"] = mock_forall
        
    def __getattr__(self, attr_name):
        if attr_name in self._static_attributes:
            return self._static_attributes[attr_name]
        # Comportement par défaut si l'attribut n'est pas statique ou géré spécifiquement
        # Lever AttributeError est le comportement standard si l'attribut n'est pas trouvé.
        # Cependant, JClass elle-même pourrait avoir d'autres attributs/méthodes.
        # Pour l'instant, on se concentre sur les attributs statiques.
        # Si on accède à un attribut qui n'est ni statique ni un attribut normal de MockJClass,
        # cela devrait lever une erreur.
        # MagicMock gère cela par défaut en créant un nouveau mock, ce qui n'est pas ce que nous voulons ici
        # pour les attributs non définis sur la classe elle-même.
        # Mais pour les attributs demandés sur l'objet JClass (pas l'instance), c'est différent.
        # La question est de savoir si JClass().ATTRIBUT ou JClass.ATTRIBUT est utilisé.
        # JPype utilise JClass('mypackage.MyClass').STATIC_FIELD.
        # Donc __getattr__ sur l'instance de MockJClass est correct.
        raise AttributeError(f"'{self.class_name}' object has no attribute '{attr_name}' and it's not a defined static attribute")

    def __call__(self, *args, **kwargs):
        # Gestion spécifique pour les collections java.util.*
        if self.class_name.startswith("java.util."):
            # Si des arguments sont passés au constructeur de la collection (ex: HashSet(initial_collection))
            # ils seront dans *args. MockJavaCollection devra les gérer.
            return MockJavaCollection(self.class_name, *args)

        instance_mock = MagicMock(name=f"MockInstanceOf_{self.class_name}")
        instance_mock._constructor_args = args
        instance_mock.class_name = self.class_name # Pour les vérifications de type
        instance_mock._collections = {} # Dictionnaire pour stocker les collections par type
        instance_mock._attributes = {} # Pour stocker des attributs simples comme maxTurns

        # Configurer getName si le premier argument est une chaîne (cas courant pour Argument, Agent)
        # Configurer getName si le premier argument est une chaîne ou un JString mocké
        if args and len(args) > 0:
            first_arg = args[0]
            if isinstance(first_arg, str):
                instance_mock.getName.return_value = first_arg
            elif isinstance(first_arg, MagicMock) and hasattr(first_arg, '_mock_jpype_jstring_value'):
                instance_mock.getName = MagicMock(return_value=first_arg._mock_jpype_jstring_value)
            else:
                instance_mock.getName.return_value = f"DefaultName_{self.class_name}"
        else:
            instance_mock.getName.return_value = f"DefaultName_{self.class_name}"

        instance_mock.toString.return_value = f"MockedToString_{self.class_name}({args})"

        # Logique pour les collections internes
        def get_collection_for_type(collection_type_name):
            if collection_type_name not in instance_mock._collections:
                instance_mock._collections[collection_type_name] = []
            return instance_mock._collections[collection_type_name]

        # La méthode 'add' sur l'instance principale pourrait ajouter à une collection "par défaut"
        # ou être plus spécifique si la classe l'exige (ex: DungTheory.add(Argument) vs DungTheory.add(Attack))
        # Pour l'instant, on suppose que 'add' ajoute à une collection 'default_elements'
        # Les tests spécifiques pourraient nécessiter de raffiner cela.
        def mock_add_to_default_collection(element):
            default_coll = get_collection_for_type("default_elements")
            default_coll.append(element)
            return True # Simuler le comportement de certaines collections Java

        # Méthodes de collection génériques qui opèrent sur un type de collection donné
        def mock_collection_size_for_type(collection_type_name):
            coll = get_collection_for_type(collection_type_name)
            print(f"[MOCK DEBUG] Taille de la collection '{collection_type_name}': {len(coll)}")
            return len(coll)

        def mock_collection_is_empty_for_type(collection_type_name):
            return len(get_collection_for_type(collection_type_name)) == 0

        def mock_collection_contains_for_type(element, collection_type_name):
            collection = get_collection_for_type(collection_type_name)
            if hasattr(element, '_constructor_args') and hasattr(element, 'class_name'): # C'est un de nos mocks
                for item in collection:
                    if hasattr(item, '_constructor_args') and hasattr(item, 'class_name'):
                        if item.class_name == element.class_name and item._constructor_args == element._constructor_args:
                            return True
            return element in collection # Fallback simple

        def mock_collection_iter_for_type(collection_type_name):
            return iter(get_collection_for_type(collection_type_name))

        # Appliquer la méthode 'add' générique à l'instance principale
        # Certaines classes comme PlBeliefSet ou DungTheory ont une méthode add directe.
        if "BeliefSet" in self.class_name or "Theory" in self.class_name:
             instance_mock.add = MagicMock(name="InstanceCollectionMethod_add", side_effect=mock_add_to_default_collection)
             # Pour size(), isEmpty(), contains() sur l'instance elle-même, elles opéreront sur 'default_elements'
             instance_mock.size = MagicMock(name="InstanceCollectionMethod_size", side_effect=lambda: mock_collection_size_for_type("default_elements"))
             instance_mock.isEmpty = MagicMock(name="InstanceCollectionMethod_isEmpty", side_effect=lambda: mock_collection_is_empty_for_type("default_elements"))
             instance_mock.contains = MagicMock(name="InstanceCollectionMethod_contains", side_effect=lambda el: mock_collection_contains_for_type(el, "default_elements"))


        # Méthodes qui retournent des collections spécifiques
        # Chaque get<CollectionType> manipulera sa propre liste dans instance_mock._collections
        methods_returning_collections_map = {
            "getNodes": "nodes",
            "getAttacks": "attacks",
            "getArguments": "arguments", # Souvent synonyme de getNodes pour DungTheory
            "getFormulas": "formulas",
            "getVariables": "variables",
            "getModels": "models" # Pour les Reasoners
        }

        for method_name, collection_key in methods_returning_collections_map.items():
            # Assurer que la collection spécifique est initialisée
            get_collection_for_type(collection_key)

            returned_collection_mock = MagicMock(name=f"ReturnedMockCollection_{method_name}")
            
            # Les opérations sur returned_collection_mock utilisent la collection spécifique
            returned_collection_mock.size = MagicMock(side_effect=lambda ck=collection_key: mock_collection_size_for_type(ck))
            returned_collection_mock.isEmpty = MagicMock(side_effect=lambda ck=collection_key: mock_collection_is_empty_for_type(ck))
            returned_collection_mock.contains = MagicMock(side_effect=lambda el, ck=collection_key: mock_collection_contains_for_type(el, ck))
            returned_collection_mock.__iter__ = MagicMock(side_effect=lambda ck=collection_key: mock_collection_iter_for_type(ck))
            
            # La méthode 'add' sur une collection retournée ne devrait typiquement pas exister ou être no-op
            # ou ajouter à CETTE collection spécifique si c'est le comportement attendu.
            # Pour l'instant, no-op pour éviter des effets de bord non désirés.
            returned_collection_mock.add = MagicMock(name=f"ReturnedCollection_{method_name}_add_noop")

            # Assigner le mock de collection retourné à la méthode de l'instance
            # Si la méthode n'existe pas encore, MagicMock la créera.
            setattr(instance_mock, method_name, MagicMock(return_value=returned_collection_mock))

        # Cas spécial pour getModel() qui retourne un seul ensemble/objet (souvent un Set de la première extension)
        # ou parfois une collection avec un seul modèle.
        # Pour l'itération, on le fait pointer vers la collection 'models' si elle existe,
        # sinon une collection 'single_model_holder'.
        if hasattr(instance_mock, "getModel"):
            # Si getModel est appelé, on s'attend à ce qu'il opère sur les 'models'
            # ou une collection dédiée si 'models' n'est pas le bon conteneur.
            # Pour l'instant, on le lie à 'models' pour la cohérence avec getModels.
            # Si un seul objet est attendu et non une collection, le testeur devra mocker différemment.
            model_collection_key = "models" # Ou "single_model_set" si on veut le distinguer
            get_collection_for_type(model_collection_key) # Assurer l'initialisation

            model_set_mock = MagicMock(name="ReturnedMockSet_getModel")
            model_set_mock.size = MagicMock(side_effect=lambda: mock_collection_size_for_type(model_collection_key))
            model_set_mock.isEmpty = MagicMock(side_effect=lambda: mock_collection_is_empty_for_type(model_collection_key))
            model_set_mock.contains = MagicMock(side_effect=lambda el: mock_collection_contains_for_type(el, model_collection_key))
            model_set_mock.__iter__ = MagicMock(side_effect=lambda: mock_collection_iter_for_type(model_collection_key))
            instance_mock.getModel.return_value = model_set_mock
            
        # Logique spécifique pour peupler les collections lors de l'appel au constructeur
        # Exemple: DungTheory(arguments_collection)
        if self.class_name == "org.tweetyproject.arg.dung.syntax.DungTheory":
            # Si le constructeur de DungTheory prend une collection d'arguments
            if len(args) == 1 and isinstance(args[0], MagicMock) and hasattr(args[0], "__iter__"):
                # On suppose que args[0] est une collection itérable d'arguments mockés
                # On les ajoute à la collection 'nodes' (ou 'arguments')
                nodes_collection = get_collection_for_type("nodes") # ou "arguments"
                for arg_element in args[0]: # itérer sur le mock de collection Java
                    nodes_collection.append(arg_element)
            # La méthode 'add' d'une DungTheory ajoute un Argument à 'nodes' et potentiellement 'arguments'
            # et une Attack à 'attacks'. Il faut surcharger 'add'.
            def dung_theory_add(element):
                if hasattr(element, 'class_name'):
                    if element.class_name == "org.tweetyproject.arg.dung.syntax.Argument":
                        nodes_coll = get_collection_for_type("nodes")
                        nodes_coll.append(element)
                        print(f"[MOCK DEBUG] DungTheory.add: Ajout de l'argument '{element.getName()}' à la collection 'nodes'. Taille actuelle: {len(nodes_coll)}")
                        return True
                    elif element.class_name == "org.tweetyproject.arg.dung.syntax.Attack":
                        attacks_coll = get_collection_for_type("attacks")
                        attacks_coll.append(element)
                        print(f"[MOCK DEBUG] DungTheory.add: Ajout de l'attaque à la collection 'attacks'. Taille actuelle: {len(attacks_coll)}")
                        return True
                # Fallback pour d'autres types ou si class_name n'est pas là
                print(f"[MOCK DEBUG] DungTheory.add: Ajout d'un élément non reconnu: {element}")
                return mock_add_to_default_collection(element)
            instance_mock.add = MagicMock(name="DungTheory_add", side_effect=dung_theory_add)


        # Gérer .equals()
        # Logique d'égalité par défaut, basée sur class_name et _constructor_args.
        # instance_mock est l'objet 'self' pour la comparaison .equals().
        # current_instance_args (maintenant instance_mock._constructor_args) sont les args du constructeur 
        # de l'instance sur laquelle .equals est appelé.
        def default_equals_logic(other_obj): # other_obj est l'objet comparé à instance_mock
            if not isinstance(other_obj, MagicMock) or \
               not hasattr(other_obj, 'class_name') or \
               not hasattr(other_obj, '_constructor_args') or \
               not hasattr(instance_mock, '_constructor_args'): # S'assurer que instance_mock a aussi des args
                return False
            
            if instance_mock.class_name != other_obj.class_name:
                return False
            
            # Comparaison des arguments du constructeur
            current_args_for_self = instance_mock._constructor_args
            other_constructor_args_for_other = other_obj._constructor_args
            
            if len(current_args_for_self) != len(other_constructor_args_for_other):
                return False
                
            for i in range(len(current_args_for_self)):
                arg_self = current_args_for_self[i]
                arg_other = other_constructor_args_for_other[i]
                
                # Si les arguments sont eux-mêmes des mocks avec une méthode equals, l'utiliser
                if hasattr(arg_self, 'equals') and callable(arg_self.equals):
                    if not arg_self.equals(arg_other): # Appelle récursivement .equals()
                        return False
                # Sinon, comparaison Python standard (pour types primitifs ou autres objets)
                elif arg_self != arg_other: # Attention: peut ne pas être sémantiquement correct pour tous les objets
                    return False
            return True

        # Logique d'égalité spécifique par classe
        if self.class_name == "org.tweetyproject.arg.dung.syntax.Argument":
            def argument_equals_side_effect(other):
                # 'other' est l'objet comparé à 'instance_mock'
                if not isinstance(other, MagicMock) or \
                   not hasattr(other, 'class_name') or other.class_name != instance_mock.class_name or \
                   not hasattr(other, '_constructor_args') or not other._constructor_args or \
                   not hasattr(instance_mock, '_constructor_args') or not instance_mock._constructor_args:
                    return False

                # Un Argument est typiquement identifié par son nom (premier arg du constructeur)
                if len(instance_mock._constructor_args) > 0 and isinstance(instance_mock._constructor_args[0], str) and \
                   len(other._constructor_args) > 0 and isinstance(other._constructor_args[0], str):
                    return instance_mock._constructor_args[0] == other._constructor_args[0]
                
                # Fallback à la logique par défaut si la structure n'est pas celle attendue (ex: pas de nom string)
                return default_equals_logic(other)
            instance_mock.equals.side_effect = argument_equals_side_effect
            
            # hashCode pour Argument
            def argument_hash_code_side_effect():
                if hasattr(instance_mock, '_constructor_args') and instance_mock._constructor_args and \
                   isinstance(instance_mock._constructor_args[0], str):
                    return hash(instance_mock._constructor_args[0])
                # Fallback si la structure n'est pas celle attendue
                return object.__hash__(instance_mock) # Ou un autre hash par défaut
            instance_mock.hashCode.side_effect = argument_hash_code_side_effect

        elif self.class_name == "org.tweetyproject.arg.dung.syntax.Attack":
            def attack_equals_side_effect(other):
                # 'other' est l'objet comparé à 'instance_mock'
                # instance_mock._constructor_args sont les args de l'objet sur lequel .equals est appelé
                if not isinstance(other, MagicMock) or \
                   not hasattr(other, 'class_name') or other.class_name != instance_mock.class_name or \
                   not hasattr(other, '_constructor_args') or len(other._constructor_args) != 2 or \
                   not hasattr(instance_mock, '_constructor_args') or len(instance_mock._constructor_args) != 2:
                    return False

                attacker_self = instance_mock._constructor_args[0]
                attacked_self = instance_mock._constructor_args[1]
                attacker_other = other._constructor_args[0]
                attacked_other = other._constructor_args[1]

                # Comparaison sémantique: les attaquants doivent être égaux ET les attaqués doivent être égaux.
                # On s'attend à ce que les composants (Arguments) aient leur propre méthode 'equals'.
                
                attacker_components_are_equal = False
                if hasattr(attacker_self, 'equals') and callable(attacker_self.equals):
                    attacker_components_are_equal = attacker_self.equals(attacker_other)
                else: # Fallback si attacker_self (composant) n'a pas .equals
                    attacker_components_are_equal = (attacker_self == attacker_other) 
                
                if not attacker_components_are_equal:
                    return False
                    
                attacked_components_are_equal = False
                if hasattr(attacked_self, 'equals') and callable(attacked_self.equals):
                    attacked_components_are_equal = attacked_self.equals(attacked_other)
                else: # Fallback si attacked_self (composant) n'a pas .equals
                    attacked_components_are_equal = (attacked_self == attacked_other)
                    
                return attacked_components_are_equal
            instance_mock.equals.side_effect = attack_equals_side_effect

            # hashCode pour Attack
            def attack_hash_code_side_effect():
                if hasattr(instance_mock, '_constructor_args') and len(instance_mock._constructor_args) == 2:
                    attacker_self = instance_mock._constructor_args[0]
                    attacked_self = instance_mock._constructor_args[1]
                    
                    # S'assurer que les composants ont hashCode
                    h_attacker = 0
                    if hasattr(attacker_self, 'hashCode') and callable(attacker_self.hashCode):
                        h_attacker = attacker_self.hashCode()
                    else: # Fallback pour les composants non mockés ou sans hashCode explicite
                        h_attacker = hash(attacker_self)
                        
                    h_attacked = 0
                    if hasattr(attacked_self, 'hashCode') and callable(attacked_self.hashCode):
                        h_attacked = attacked_self.hashCode()
                    else: # Fallback
                        h_attacked = hash(attacked_self)
                        
                    return hash((h_attacker, h_attacked))
                # Fallback si la structure n'est pas celle attendue
                return object.__hash__(instance_mock) # Ou un autre hash par défaut
            instance_mock.hashCode.side_effect = attack_hash_code_side_effect
        
        # Ajoutez d'autres logiques spécifiques pour .equals() ici si nécessaire:
        # elif self.class_name == "org.tweetyproject.some.other.Class":
        #     def specific_equals_logic(other):
        #         # ... votre logique ...
        #         return result
        #     instance_mock.equals.side_effect = specific_equals_logic
            
        else:
            # Pour toutes les autres classes, utiliser la logique d'égalité par défaut.
            # S'assurer que instance_mock est bien l'objet sur lequel .equals est appelé.
            # La fonction default_equals_logic prend 'other_obj' comme argument.
            # Le 'self' implicite de default_equals_logic sera 'instance_mock'.
            instance_mock.equals.side_effect = default_equals_logic
            
            # hashCode par défaut pour les autres classes
            # Si equals est basé sur _constructor_args, hashCode devrait l'être aussi.
            def default_hash_code_logic():
                if hasattr(instance_mock, '_constructor_args'):
                    # Créer un tuple des arguments pour le rendre hashable.
                    # Si les arguments eux-mêmes ne sont pas hashables, cela échouera.
                    # Une version plus robuste pourrait hasher les représentations str ou les hashCodes individuels.
                    try:
                        # Tenter de hasher les args directement s'ils sont primitifs ou ont un bon __hash__
                        # Pour les mocks, il faut utiliser leur .hashCode() s'il existe.
                        hashed_args = []
                        for arg in instance_mock._constructor_args:
                            if hasattr(arg, 'hashCode') and callable(arg.hashCode):
                                hashed_args.append(arg.hashCode())
                            elif isinstance(arg, MagicMock): # Si c'est un mock sans .hashCode() explicite
                                hashed_args.append(object.__hash__(arg)) # Utiliser le hash de l'objet mock
                            else:
                                hashed_args.append(hash(arg)) # Pour les types Python normaux
                        return hash(tuple(hashed_args))
                    except TypeError:
                        # Si un argument n'est pas hashable, fallback
                        return object.__hash__(instance_mock)
                return object.__hash__(instance_mock) # Hash de l'objet mock lui-même
            instance_mock.hashCode.side_effect = default_hash_code_logic

        # Ajouter __eq__ et __hash__ pour la compatibilité avec les collections Python
        # qui utilisent ces méthodes pour l'égalité et le hachage.
        # Ces méthodes délégueront aux méthodes equals() et hashCode() mockées.
        def __eq__side_effect(other):
            if hasattr(instance_mock, 'equals') and callable(instance_mock.equals):
                return instance_mock.equals(other)
            return NotImplemented # Indique que la comparaison n'est pas implémentée par ce type

        def __hash__side_effect():
            if hasattr(instance_mock, 'hashCode') and callable(instance_mock.hashCode):
                return instance_mock.hashCode()
            return object.__hash__(instance_mock) # Fallback

        instance_mock.__eq__.side_effect = __eq__side_effect
        instance_mock.__hash__.side_effect = __hash__side_effect

# Logique pour FormulaParser.parseFormula()
        # Cette section doit être avant les configurations spécifiques de formules (comme QBF ci-dessous)
        # car elle crée les instances de formules qui pourraient ensuite être configurées.
        formula_class_map = {
            "net.sf.tweety.logics.pl.parser.PlParser": "net.sf.tweety.logics.pl.syntax.PropositionalFormula",
            "net.sf.tweety.logics.fol.parser.FolParser": "net.sf.tweety.logics.fol.syntax.FolFormula",
            "org.tweetyproject.logics.qbf.parser.QbfParser": "org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula",
            # TODO: Ajouter d'autres parsers si nécessaire, ex:
            # "org.tweetyproject.logics.cl.parser.ClParser": "org.tweetyproject.logics.cl.syntax.ClFormula",
        }

        if self.class_name in formula_class_map:
            expected_formula_class_name = formula_class_map[self.class_name]

            def mock_parse_formula(formula_string, *args_parser): # formula_string est l'argument de parseFormula
                # args_parser capture d'éventuels arguments supplémentaires passés à parseFormula
                parsed_formula_mock = MagicMock(name=f"ParsedFormula_{expected_formula_class_name}_{str(formula_string)[:30]}")
                parsed_formula_mock.class_name = expected_formula_class_name
                # Stocker la formule originale et les autres args pour la traçabilité et .equals()
                parsed_formula_mock._constructor_args = (formula_string,) + args_parser 
                parsed_formula_mock.toString.return_value = str(formula_string)

                # Logique d'égalité pour les formules parsées
                def formula_equals_logic(other_formula):
                    if not isinstance(other_formula, MagicMock) or \
                       not hasattr(other_formula, 'class_name') or \
                       not hasattr(other_formula, '_constructor_args'):
                        return False
                    
                    # Comparer class_name
                    if parsed_formula_mock.class_name != other_formula.class_name:
                        return False
                    
                    # Comparer les arguments du constructeur (qui incluent la chaîne de formule)
                    if parsed_formula_mock._constructor_args != other_formula._constructor_args:
                        return False
                        
                    return True
                
                parsed_formula_mock.equals = MagicMock(name=f"{expected_formula_class_name}_equals", side_effect=formula_equals_logic)
                
                # Note: Si la formule retournée est une QuantifiedBooleanFormula, des comportements spécifiques
                # (comme getQuantifier, getVariables) sont gérés par la logique QBF plus bas lorsque
                # JClass("...QuantifiedBooleanFormula") est instanciée directement.
                # Ce mock de formule parsée se concentre sur avoir le bon class_name et une base de .equals().
                # Des comportements plus spécifiques pourraient être ajoutés à parsed_formula_mock si nécessaire.

                return parsed_formula_mock

            instance_mock.parseFormula = MagicMock(name=f"{self.class_name}_parseFormula", side_effect=mock_parse_formula)
        # Gérer getQuantifier pour QuantifiedBooleanFormula
        if self.class_name == "org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula":
            if args and len(args) > 0 and args[0] in ("EXISTS_MOCK_VALUE", "FORALL_MOCK_VALUE"):
                 instance_mock.getQuantifier.return_value = args[0]
            else: # Fallback
                 instance_mock.getQuantifier.return_value = "MOCK_QBF_UNKNOWN_QUANTIFIER_FALLBACK"
            
            # Correction pour getVariables() pour QBF
            # Le deuxième argument du constructeur est censé être un JArray de Variable
            if len(args) > 1:
                qbf_variables_arg = args[1]
                variables_collection = get_collection_for_type("variables") # Assure l'initialisation
                variables_collection.clear() # Vider au cas où

                if isinstance(qbf_variables_arg, MagicMock) and hasattr(qbf_variables_arg, '_mock_jpype_array_elements'):
                    # Si JArray est mocké pour avoir _mock_jpype_array_elements
                    for var_element in qbf_variables_arg._mock_jpype_array_elements:
                        variables_collection.append(var_element)
                elif isinstance(qbf_variables_arg, (list, tuple)): # Si on passe une liste Python directement
                    for var_element in qbf_variables_arg:
                        variables_collection.append(var_element)
                # Si qbf_variables_arg est un seul mock de Variable (pas une collection)
                elif isinstance(qbf_variables_arg, MagicMock) and qbf_variables_arg.class_name == "org.tweetyproject.logics.fol.syntax.Variable":
                     variables_collection.append(qbf_variables_arg)


            # Assurer que getVariables() sur l'instance QBF utilise cette collection "variables"
            qbf_vars_collection_mock = MagicMock(name="ReturnedMockCollection_QBF_getVariables")
            qbf_vars_collection_mock.size = MagicMock(side_effect=lambda: mock_collection_size_for_type("variables"))
            qbf_vars_collection_mock.isEmpty = MagicMock(side_effect=lambda: mock_collection_is_empty_for_type("variables"))
            qbf_vars_collection_mock.contains = MagicMock(side_effect=lambda el: mock_collection_contains_for_type(el, "variables"))
            qbf_vars_collection_mock.__iter__ = MagicMock(side_effect=lambda: mock_collection_iter_for_type("variables"))
            instance_mock.getVariables.return_value = qbf_vars_collection_mock


        # Pour les méthodes comme inconsistencyMeasure qui devraient retourner un nombre
        if "InconsistencyMeasure" in self.class_name:
            instance_mock.inconsistencyMeasure.return_value = 0.0 # Ou 1.0 pour indiquer une inconsistance par défaut

        # Gestion générique des getters/setters simples comme getMaxTurns/setMaxTurns
        # Initialiser les valeurs par défaut pour les attributs connus
        if self.class_name == "org.tweetyproject.agents.dialogues.protocols.PersuasionProtocol":
            instance_mock._attributes['_max_turns'] = 0 # Valeur par défaut pour maxTurns

        # Configurer setMaxTurns
        if hasattr(instance_mock, "setMaxTurns"):
            def mock_set_max_turns(value):
                instance_mock._attributes['_max_turns'] = value
            instance_mock.setMaxTurns = MagicMock(name=f"{self.class_name}_setMaxTurns", side_effect=mock_set_max_turns)

        # Configurer getMaxTurns
        if hasattr(instance_mock, "getMaxTurns"):
            def mock_get_max_turns():
                return instance_mock._attributes.get('_max_turns', 0) # Retourne 0 si non défini
            instance_mock.getMaxTurns = MagicMock(name=f"{self.class_name}_getMaxTurns", side_effect=mock_get_max_turns)
            
        # Logique pour les Reasoners (Prover, etc.) pour peupler les modèles
        if "Reasoner" in self.class_name or "Prover" in self.class_name:
            def mock_add_model_to_results(model_element):
                models_coll = get_collection_for_type("models")
                models_coll.append(model_element)
                return True # Simuler un ajout réussi

            # Les reasoners ont souvent une méthode solve() ou query().
            # On peut ajouter une méthode 'addModelToResults' pour que les tests puissent simuler
            # le peuplement des modèles après un 'solve' fictif.
            instance_mock.addModelToResults = MagicMock(name="Reasoner_addModelToResults", side_effect=mock_add_model_to_results)
            
            # Si un reasoner est directement itérable (rare, mais pour couvrir)
            # ou si son 'solve' retourne directement une collection itérable de modèles.
            # Pour l'instant, on se fie à getModels() et getModel().

        # Logique pour les Reasoners (Prover, etc.) pour peupler les modèles
        if self.class_name == "net.sf.tweety.arg.dung.reasoner.CompleteReasoner":
            # Simuler les extensions complètes: {a}, {b}, {}
            # Nécessite d'accéder aux arguments créés dans le test.
            # Pour un mock, on peut soit les passer au constructeur du reasoner,
            # soit les créer ici de manière générique.
            # Dans un vrai scénario, le reasoner prendrait une DungTheory.
            # Ici, on simule le résultat de getModels().
            models_coll = get_collection_for_type("models")
            
            # Créer des mocks pour les arguments 'a' et 'b'
            mock_arg_a = MagicMock(name="MockArgument_a")
            mock_arg_a.getName.return_value = "a"
            mock_arg_a.equals.side_effect = lambda other: hasattr(other, 'getName') and other.getName() == "a"
            mock_arg_a.hashCode.side_effect = lambda: hash("a")
            mock_arg_a.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
            mock_arg_a._constructor_args = ("a",)

            mock_arg_b = MagicMock(name="MockArgument_b")
            mock_arg_b.getName.return_value = "b"
            mock_arg_b.equals.side_effect = lambda other: hasattr(other, 'getName') and other.getName() == "b"
            mock_arg_b.hashCode.side_effect = lambda: hash("b")
            mock_arg_b.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
            mock_arg_b._constructor_args = ("b",)

            # Extensions attendues: {a}, {b}, {}
            # Chaque extension est un Set Java (simulé par MockJavaCollection)
            HashSet = JClass("java.util.HashSet") # Utiliser notre JClass mocké pour HashSet

            ext1 = HashSet()
            ext1.add(mock_arg_a)
            models_coll.append(ext1)

            ext2 = HashSet()
            ext2.add(mock_arg_b)
            models_coll.append(ext2)

            ext3 = HashSet() # Ensemble vide
            models_coll.append(ext3)
            
            print(f"[MOCK DEBUG] CompleteReasoner: Ajout de {len(models_coll)} extensions mockées.")

        elif self.class_name == "net.sf.tweety.arg.dung.reasoner.StableReasoner":
            # Simuler l'extension stable: {a, c}
            models_coll = get_collection_for_type("models")

            mock_arg_a = MagicMock(name="MockArgument_a")
            mock_arg_a.getName.return_value = "a"
            mock_arg_a.equals.side_effect = lambda other: hasattr(other, 'getName') and other.getName() == "a"
            mock_arg_a.hashCode.side_effect = lambda: hash("a")
            mock_arg_a.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
            mock_arg_a._constructor_args = ("a",)

            mock_arg_c = MagicMock(name="MockArgument_c")
            mock_arg_c.getName.return_value = "c"
            mock_arg_c.equals.side_effect = lambda other: hasattr(other, 'getName') and other.getName() == "c"
            mock_arg_c.hashCode.side_effect = lambda: hash("c")
            mock_arg_c.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
            mock_arg_c._constructor_args = ("c",)

            HashSet = JClass("java.util.HashSet")

            ext1 = HashSet()
            ext1.add(mock_arg_a)
            ext1.add(mock_arg_c)
            models_coll.append(ext1)
            
            print(f"[MOCK DEBUG] StableReasoner: Ajout de {len(models_coll)} extensions mockées.")

        return instance_mock

# Classe pour simuler les collections Java de java.util
class MockJavaCollection:
    def __init__(self, java_class_name, *constructor_args):
        self.class_name = java_class_name
        self._constructor_args = constructor_args
        self._internal_collection = self._determine_internal_collection_type()

        # Si un argument est passé au constructeur (ex: new HashSet(anotherCollection))
        # On essaie de peupler la collection interne.
        if constructor_args:
            initial_data = constructor_args[0]
            if hasattr(initial_data, '__iter__'):
                try:
                    for item in initial_data:
                        self.add(item)
                except TypeError: # Peut arriver si initial_data n'est pas vraiment itérable malgré __iter__
                    print(f"[MOCK WARNING] MockJavaCollection pour {self.class_name} a reçu un argument de constructeur non itérable: {initial_data}")
            elif initial_data is not None: # Gérer le cas où ce n'est pas une collection mais un seul élément ? (rare pour constructeurs de collection)
                print(f"[MOCK WARNING] MockJavaCollection pour {self.class_name} a reçu un argument de constructeur non-collection: {initial_data}")


    def _determine_internal_collection_type(self):
        if "Set" in self.class_name or "HashSet" in self.class_name:
            return set()
        # Pour List, ArrayList, Collection, et par défaut
        return []

    def add(self, element):
        if isinstance(self._internal_collection, list):
            self._internal_collection.append(element)
            return True # List.add retourne void en Java, mais Collection.add retourne boolean. On simule Collection.
        elif isinstance(self._internal_collection, set):
            # Set.add retourne True si l'élément n'était pas déjà présent
            is_new = element not in self._internal_collection
            self._internal_collection.add(element)
            return is_new
        return False

    def size(self):
        return len(self._internal_collection)

    def isEmpty(self):
        return len(self._internal_collection) == 0

    def contains(self, element):
        # Pour les sets, la recherche est efficace. Pour les listes, c'est une recherche linéaire.
        # La logique de comparaison d'éléments mockés peut être complexe.
        # On utilise la logique de `mock_collection_contains_for_type` si possible,
        # sinon une simple vérification `in`.
        if hasattr(element, '_constructor_args') and hasattr(element, 'class_name'):
            for item in self._internal_collection:
                if hasattr(item, '_constructor_args') and hasattr(item, 'class_name'):
                    if item.class_name == element.class_name and item._constructor_args == element._constructor_args:
                        return True
        return element in self._internal_collection

    def remove(self, element):
        try:
            if isinstance(self._internal_collection, list):
                self._internal_collection.remove(element)
                return True # List.remove(Object) retourne boolean
            elif isinstance(self._internal_collection, set):
                # Set.remove retourne True si l'élément était présent
                if element in self._internal_collection:
                    self._internal_collection.remove(element)
                    return True
                return False
        except ValueError: # element not in list
            return False
        return False # Par défaut

    def clear(self):
        self._internal_collection.clear()

    def __iter__(self):
        return iter(self._internal_collection)

    def toString(self):
        # Simuler la sortie [elem1, elem2, ...] pour List ou Set
        return str(list(self._internal_collection)) # Convertir en liste pour une représentation cohérente

    def equals(self, other):
        if not isinstance(other, MockJavaCollection) or self.class_name != other.class_name:
            return False
        if self.size() != other.size():
            return False
        
        # Pour les listes, l'ordre compte. Pour les sets, non.
        if isinstance(self._internal_collection, list):
            # Doit aussi vérifier l'égalité des éléments eux-mêmes, potentiellement récursivement
            # Ceci est une simplification. Une vraie égalité de listes mockées nécessiterait
            # d'appeler .equals() sur chaque paire d'éléments.
            return list(self) == list(other) # Comparaison simplifiée
        elif isinstance(self._internal_collection, set):
            # Comparaison d'ensembles, l'ordre ne compte pas.
            # Nécessite que les éléments soient hashables et aient une égalité correcte.
            return self._internal_collection == other._internal_collection # Comparaison simplifiée
        return False

    # D'autres méthodes pourraient être ajoutées ici (toArray, etc.)

def JClass(name):
    """Simule jpype.JClass()."""
    return MockJClass(name)
 
def JArray(type_): # type_ est la classe des éléments, ex: JClass("org.tweetyproject.logics.fol.syntax.Variable")
    """Simule jpype.JArray()."""
    # On retourne un mock qui peut stocker des éléments et être itéré.
    # On a besoin de cela pour que le constructeur de QBF puisse recevoir une "collection" de variables.
    array_mock = MagicMock(name=f"MockJArray_of_{type_.__name__ if hasattr(type_, '__name__') else str(type_)}")
    array_mock._mock_jpype_array_elements = []
    
    def array_add(element):
        array_mock._mock_jpype_array_elements.append(element)
        return True # Comportement typique de .add pour certaines collections Java
    
    def array_len():
        return len(array_mock._mock_jpype_array_elements)

    def array_iter():
        return iter(array_mock._mock_jpype_array_elements)

    def array_getitem(index):
        return array_mock._mock_jpype_array_elements[index]

    array_mock.add = MagicMock(side_effect=array_add)
    array_mock.__len__ = MagicMock(side_effect=array_len) # Pour que len(jarray_mock) fonctionne
    array_mock.__iter__ = MagicMock(side_effect=array_iter) # Pour que for el in jarray_mock fonctionne
    array_mock.__getitem__ = MagicMock(side_effect=array_getitem) # Pour accès par index

    # Si le constructeur de JArray est appelé avec une taille (ex: JArray(JString, 5))
    # ou avec une liste d'initialisation (plus complexe à mocker ici sans savoir comment JPype le fait)
    # Pour l'instant, on se concentre sur un JArray vide auquel on ajoute des éléments.
    return array_mock

def JString(value):
    """Simule jpype.JString()."""
    # Retourne un mock qui se comporte comme une chaîne mais stocke la valeur originale
    jstring_mock = MagicMock(name=f"MockJString_{str(value)[:20]}")
    jstring_mock._mock_jpype_jstring_value = str(value)
    jstring_mock.toString.return_value = str(value)
    jstring_mock.__str__.return_value = str(value)
    jstring_mock.__repr__.return_value = f"JString('{str(value)}')"
    # Permettre la comparaison directe avec des chaînes Python
    jstring_mock.__eq__.side_effect = lambda other: str(value) == other
    jstring_mock.__hash__.side_effect = lambda: hash(str(value))
    return jstring_mock

def JBoolean(value):
    """Simule jpype.JBoolean()."""
    # Utilise JObject pour encapsuler la valeur booléenne et son type Java.
    # JClass("java.lang.Boolean") est un mock de la classe Java Boolean.
    return JObject(value, JClass("java.lang.Boolean"))

def JInt(value):
    """Simule jpype.JInt()."""
    return JObject(value, JClass("java.lang.Integer"))

def JDouble(value):
    """Simule jpype.JDouble()."""
    return JObject(value, JClass("java.lang.Double"))

# Classes Java simulées
class JObject:
    """Simule jpype.JObject."""
    def __init__(self, *args, **kwargs):
        self.args = args  # Conserver pour débogage ou compatibilité
        self.kwargs = kwargs

        self._actual_value = None
        self._java_type_name = None  # Stocker le nom de la classe Java, ex: "java.lang.Double"

        if len(args) == 2:
            self._actual_value = args[0]  # La valeur Python primitive
            java_type_arg = args[1]     # Le type Java mocké, ex: JClass("java.lang.Double")
            if hasattr(java_type_arg, 'class_name'):  # Si c'est un MockJClass
                self._java_type_name = java_type_arg.class_name
            elif isinstance(java_type_arg, str):  # Si on passe le nom de la classe directement (moins probable)
                self._java_type_name = java_type_arg
            # Si java_type_arg n'est ni l'un ni l'autre, _java_type_name reste None,
            # et les appels à xxxValue() lèveront une AttributeError.
        # Si args n'a pas la longueur 2, _actual_value et _java_type_name restent None,
        # ce qui est un état invalide pour appeler xxxValue().

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
            return int(self._actual_value) # Python int gère les longs
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
            return int(self._actual_value) # Java byte est -128 à 127, Python int convient
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'byteValue'")

    def charValue(self):
        if self._java_type_name == "java.lang.Character":
            # Assurer que la valeur est une chaîne et, idéalement, d'un seul caractère.
            # La conversion en str() gère la plupart des cas.
            char_val = str(self._actual_value)
            # En Java, un char ne peut pas être null, mais _actual_value pourrait être None.
            # Si _actual_value est None, str(None) est "None".
            # Le comportement exact pour un char null dépend de JPype.
            # Pour un mock, retourner str() est une approximation raisonnable.
            return char_val
        raise AttributeError(f"'JObject' of type '{self._java_type_name or 'unknown'}' has no attribute 'charValue'")

class JException(Exception):
    """Simule jpype.JException."""
    def __init__(self, message="Mock Java Exception"):
        super().__init__(message)
        self.message = message
    
    def getClass(self):
        """Simule la méthode getClass() de Java."""
        class MockClass:
            def getName(self):
                return "org.mockexception.MockException"
        return MockClass()
    
    def getMessage(self):
        """Simule la méthode getMessage() de Java."""
        return self.message

class JVMNotFoundException(Exception):
    """Simule jpype.JVMNotFoundException."""
    pass

# Mock pour jpype.imports
class MockImportsModule:
    def __init__(self):
        self._registered_domains = {}

    def registerDomain(self, domain_name, alias=None):
        # Simule l'enregistrement d'un domaine.
        # Pour l'instant, on ne fait rien de spécial avec, mais on pourrait stocker l'info.
        actual_alias = alias if alias else domain_name
        self._registered_domains[domain_name] = actual_alias
        mock_logger.info(f"jpype.imports.registerDomain: Registered domain '{domain_name}' with alias '{actual_alias}'")

    # Ajouter d'autres méthodes de jpype.imports si nécessaire
    # par exemple, getDomain(domain_name)

imports = MockImportsModule()


# Installer le mock dans sys.modules
# ATTENTION: Ces lignes sont commentées car elles causent des problèmes avec les tests d'intégration
# qui ont besoin du vrai module jpype. Les tests nécessitant le mock devraient l'activer explicitement.
# if 'jpype' not in sys.modules or 'tests.mocks.jpype_mock' not in sys.modules['jpype'].__file__:
#     sys.modules['jpype'] = sys.modules[__name__]
#     mock_logger.info("Mock activé pour 'jpype'")
# else:
#     mock_logger.info("Mock pour 'jpype' déjà présent ou est le vrai module, non remplacé.")

# if 'jpype1' not in sys.modules or 'tests.mocks.jpype_mock' not in sys.modules['jpype1'].__file__:
#     sys.modules['jpype1'] = sys.modules[__name__]
#     mock_logger.info("Mock activé pour 'jpype1'")
# else:
#     mock_logger.info("Mock pour 'jpype1' déjà présent ou est le vrai module, non remplacé.")


mock_logger.info("Mock JPype1 (jpype_mock.py) initialisé. Le patch global sys.modules est DÉSACTIVÉ.")
