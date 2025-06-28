"""
Interface avec TweetyProject pour la validation logique des contre-arguments.

Ce module fournit une interface avec la bibliothèque Java TweetyProject
pour la validation formelle des arguments et contre-arguments.
"""

import os
import logging
import tempfile
from typing import Dict, List, Any, Optional, Tuple

import jpype
import jpype.imports
from jpype.types import *

from ..agent.definitions import Argument, CounterArgument, CounterArgumentType, ArgumentStrength

logger = logging.getLogger(__name__)


class TweetyBridge:
    """
    Classe pour interfacer avec TweetyProject via JPype.
    """
    
    def __init__(self, tweety_jar_path: Optional[str] = None):
        """
        Initialise l'interface avec TweetyProject.
        
        Args:
            tweety_jar_path: Chemin vers le fichier JAR de TweetyProject
        """
        # Définir le chemin par défaut vers le JAR de TweetyProject
        if tweety_jar_path is None:
            # Essayer de trouver le JAR dans un dossier standard
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', '..', 'libs', 'tweety-full.jar'),
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'libs', 'tweety-full.jar'),
                os.path.join(os.path.dirname(__file__), '..', '..', '..', '2025-Epita-Intelligence-Symbolique-sujet-2.3.3', 'libs', 'tweety-full.jar')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    tweety_jar_path = path
                    break
        
        if tweety_jar_path is None or not os.path.exists(tweety_jar_path):
            logger.warning("Fichier JAR de TweetyProject non trouvé. La validation formelle ne sera pas disponible.")
            self.tweety_available = False
            return
        
        self.tweety_jar_path = tweety_jar_path
        self.tweety_available = True
        
        # Démarrer la JVM si elle n'est pas déjà démarrée
        self._start_jvm()
        
        # Importer les classes nécessaires de TweetyProject
        self._import_tweety_classes()
        
        logger.info("TweetyBridge initialisé avec succès")
    
    def _start_jvm(self):
        """Démarre la JVM avec les bons paramètres."""
        if not jpype.isJVMStarted():
            logger.info(f"Démarrage de la JVM avec le JAR: {self.tweety_jar_path}")
            try:
                jpype.startJVM(jpype.getDefaultJVMPath(), f"-Djava.class.path={self.tweety_jar_path}")
                logger.info("JVM démarrée avec succès")
            except Exception as e:
                logger.error(f"Erreur lors du démarrage de la JVM: {e}")
                self.tweety_available = False
        else:
            logger.info("JVM déjà démarrée")
    
    def _import_tweety_classes(self):
        """Importe les classes nécessaires de TweetyProject."""
        if not self.tweety_available:
            return
        
        try:
            # Importer les packages Java nécessaires
            from org.tweetyproject.arg.dung.syntax import DungTheory, Argument as TweetyArgument, Attack
            from org.tweetyproject.arg.dung.reasoner import AbstractExtensionReasoner, SimpleGroundedReasoner, SimpleCompleteReasoner
            from org.tweetyproject.arg.dung.semantics import Extension, Semantics
            
            # Stocker les références aux classes
            self.DungTheory = DungTheory
            self.TweetyArgument = TweetyArgument
            self.Attack = Attack
            self.SimpleGroundedReasoner = SimpleGroundedReasoner
            self.SimpleCompleteReasoner = SimpleCompleteReasoner
            self.Extension = Extension
            self.Semantics = Semantics
            
            logger.info("Classes TweetyProject importées avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'importation des classes TweetyProject: {e}")
            self.tweety_available = False
    
    def validate_counter_argument(
        self, 
        original_arg: Argument, 
        counter_arg: CounterArgument
    ) -> Dict[str, Any]:
        """
        Valide un contre-argument en utilisant TweetyProject.
        
        Args:
            original_arg: L'argument original
            counter_arg: Le contre-argument à valider
            
        Returns:
            Un dictionnaire contenant les résultats de la validation
        """
        if not self.tweety_available:
            logger.warning("TweetyProject n'est pas disponible. Validation simplifiée utilisée.")
            return self._fallback_validation(original_arg, counter_arg)
        
        try:
            logger.info("Utilisation de la validation formelle avec TweetyProject")
            # Créer une théorie de Dung
            theory = self.DungTheory()
            
            # Créer les arguments
            original_argument = self.TweetyArgument(str(id(original_arg)))
            counter_argument = self.TweetyArgument(str(id(counter_arg)))
            
            theory.add(original_argument)
            theory.add(counter_argument)
            
            # Modéliser l'attaque en fonction du type de contre-argument
            self._add_attack_based_on_type(theory, counter_arg, original_argument, counter_argument)
            
            # Calculer les extensions selon différentes sémantiques
            grounded_reasoner = self.SimpleGroundedReasoner()
            complete_reasoner = self.SimpleCompleteReasoner()
            
            grounded_extension = grounded_reasoner.getModel(theory)
            complete_extensions = complete_reasoner.getModels(theory)
            
            # Analyser les résultats
            original_in_grounded = self._is_in_extension(original_argument, grounded_extension)
            counter_in_grounded = self._is_in_extension(counter_argument, grounded_extension)
            
            original_in_complete = any(self._is_in_extension(original_argument, ext) for ext in complete_extensions)
            counter_in_complete = any(self._is_in_extension(counter_argument, ext) for ext in complete_extensions)
            
            # Calculer les résultats
            is_valid_attack = counter_in_grounded and not original_in_grounded
            original_survives = original_in_complete
            counter_succeeds = counter_in_grounded or counter_in_complete
            logical_consistency = len(complete_extensions) > 0
            
            # Construire la représentation formelle
            formal_repr = self._build_formal_representation(theory)
            
            logger.info(f"Validation formelle terminée: is_valid_attack={is_valid_attack}, original_survives={original_survives}, counter_succeeds={counter_succeeds}")
            
            return {
                'is_valid_attack': is_valid_attack,
                'original_survives': original_survives,
                'counter_succeeds': counter_succeeds,
                'logical_consistency': logical_consistency,
                'formal_representation': formal_repr,
                'extensions': {
                    'grounded': self._extension_to_string(grounded_extension),
                    'complete': [self._extension_to_string(ext) for ext in complete_extensions]
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation avec TweetyProject: {e}")
            return self._fallback_validation(original_arg, counter_arg)
    
    def assess_argument_strength(
        self, 
        original_arg: Argument,
        counter_args: List[CounterArgument]
    ) -> float:
        """
        Évalue la force d'un argument après application de contre-arguments.
        
        Args:
            original_arg: L'argument original
            counter_args: Liste des contre-arguments
            
        Returns:
            Un score entre 0 et 1 représentant la force de l'argument
        """
        if not self.tweety_available or not counter_args:
            logger.warning("TweetyProject n'est pas disponible ou pas de contre-arguments. Évaluation simplifiée utilisée.")
            return self._fallback_strength_assessment(original_arg, counter_args)
        
        try:
            # Créer une théorie de Dung
            theory = self.DungTheory()
            
            # Créer l'argument original
            original_argument = self.TweetyArgument(str(id(original_arg)))
            theory.add(original_argument)
            
            # Ajouter les contre-arguments
            counter_arguments = []
            for i, counter_arg in enumerate(counter_args):
                counter_argument = self.TweetyArgument(f"counter_{i}")
                theory.add(counter_argument)
                counter_arguments.append((counter_arg, counter_argument))
                
                # Ajouter l'attaque
                self._add_attack_based_on_type(theory, counter_arg, original_argument, counter_argument)
            
            # Calculer les extensions selon différentes sémantiques
            grounded_reasoner = self.SimpleGroundedReasoner()
            complete_reasoner = self.SimpleCompleteReasoner()
            
            grounded_extension = grounded_reasoner.getModel(theory)
            complete_extensions = complete_reasoner.getModels(theory)
            
            # Analyser la survie de l'argument original
            original_in_grounded = self._is_in_extension(original_argument, grounded_extension)
            
            # Calculer le taux d'acceptation dans les extensions complètes
            if complete_extensions:
                acceptance_rate = sum(1 for ext in complete_extensions if self._is_in_extension(original_argument, ext)) / len(complete_extensions)
            else:
                acceptance_rate = 0.0
            
            # Ajuster le score en fonction de la présence dans l'extension fondée
            if original_in_grounded:
                acceptance_rate = (acceptance_rate + 1) / 2
            
            return acceptance_rate
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation de la force avec TweetyProject: {e}")
            return self._fallback_strength_assessment(original_arg, counter_args)
    
    def generate_attack_graph(
        self, 
        original_arg: Argument,
        counter_args: List[CounterArgument]
    ) -> str:
        """
        Génère une représentation textuelle du graphe d'attaque.
        
        Args:
            original_arg: L'argument original
            counter_args: Liste des contre-arguments
            
        Returns:
            Une représentation textuelle du graphe d'attaque
        """
        if not self.tweety_available or not counter_args:
            return "Graphe d'attaque non disponible."
        
        try:
            # Créer une théorie de Dung
            theory = self.DungTheory()
            
            # Créer l'argument original
            original_argument = self.TweetyArgument("original")
            theory.add(original_argument)
            
            # Ajouter les contre-arguments
            for i, counter_arg in enumerate(counter_args):
                counter_argument = self.TweetyArgument(f"counter_{i}")
                theory.add(counter_argument)
                
                # Ajouter l'attaque
                self._add_attack_based_on_type(theory, counter_arg, original_argument, counter_argument)
            
            # Construire la représentation formelle
            return self._build_formal_representation(theory)
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du graphe d'attaque: {e}")
            return f"Erreur: {str(e)}"
    
    def _add_attack_based_on_type(
        self, 
        theory, 
        counter_arg: CounterArgument, 
        original_argument, 
        counter_argument
    ):
        """
        Ajoute une attaque à la théorie en fonction du type de contre-argument.
        
        Args:
            theory: La théorie de Dung
            counter_arg: Le contre-argument
            original_argument: L'argument original (objet TweetyProject)
            counter_argument: Le contre-argument (objet TweetyProject)
        """
        # Créer différents types d'attaques en fonction du type de contre-argument
        if counter_arg.counter_type == CounterArgumentType.DIRECT_REFUTATION:
            # Attaque directe
            attack = self.Attack(counter_argument, original_argument)
            theory.add(attack)
        
        elif counter_arg.counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            # Attaque sur les prémisses (modélisée comme une attaque sur l'argument)
            attack = self.Attack(counter_argument, original_argument)
            theory.add(attack)
        
        elif counter_arg.counter_type == CounterArgumentType.COUNTER_EXAMPLE:
            # Un contre-exemple attaque la généralisation
            attack = self.Attack(counter_argument, original_argument)
            theory.add(attack)
        
        elif counter_arg.counter_type == CounterArgumentType.ALTERNATIVE_EXPLANATION:
            # Une explication alternative peut coexister avec l'argument original
            # On pourrait ajouter un nouvel argument pour la conclusion et faire attaquer les deux
            conclusion_arg = self.TweetyArgument("conclusion")
            theory.add(conclusion_arg)
            
            support1 = self.Attack(original_argument, conclusion_arg)
            support2 = self.Attack(counter_argument, conclusion_arg)
            
            theory.add(support1)
            theory.add(support2)
        
        elif counter_arg.counter_type == CounterArgumentType.REDUCTIO_AD_ABSURDUM:
            # Réduction à l'absurde attaque directement l'argument
            attack = self.Attack(counter_argument, original_argument)
            theory.add(attack)
        
        else:
            # Attaque par défaut
            attack = self.Attack(counter_argument, original_argument)
            theory.add(attack)
    
    def _is_in_extension(self, argument, extension) -> bool:
        """
        Vérifie si un argument est dans une extension.
        
        Args:
            argument: L'argument à vérifier
            extension: L'extension à vérifier
            
        Returns:
            True si l'argument est dans l'extension, False sinon
        """
        try:
            return extension.contains(argument)
        except:
            return False
    
    def _extension_to_string(self, extension) -> str:
        """
        Convertit une extension en chaîne de caractères.
        
        Args:
            extension: L'extension à convertir
            
        Returns:
            Une représentation textuelle de l'extension
        """
        try:
            return str(extension)
        except:
            return "Extension non disponible"
    
    def _build_formal_representation(self, theory) -> str:
        """
        Construit une représentation formelle d'une théorie de Dung.
        
        Args:
            theory: La théorie de Dung
            
        Returns:
            Une représentation textuelle de la théorie
        """
        try:
            return str(theory)
        except:
            return "Représentation formelle non disponible"
    
    def _fallback_validation(
        self, 
        original_arg: Argument, 
        counter_arg: CounterArgument
    ) -> Dict[str, Any]:
        """
        Méthode de secours pour la validation si TweetyProject n'est pas disponible.
        
        Args:
            original_arg: L'argument original
            counter_arg: Le contre-argument à valider
            
        Returns:
            Un dictionnaire contenant les résultats de la validation
        """
        logger.warning("Utilisation de la validation simplifiée (fallback)")
        
        # Validation simplifiée basée sur le type et la force du contre-argument
        is_valid_attack = True
        original_survives = counter_arg.strength in [ArgumentStrength.WEAK, ArgumentStrength.MODERATE]
        counter_succeeds = counter_arg.strength in [ArgumentStrength.MODERATE, ArgumentStrength.STRONG, ArgumentStrength.DECISIVE]
        logical_consistency = True
        
        logger.info(f"Validation fallback terminée: is_valid_attack={is_valid_attack}, original_survives={original_survives}, counter_succeeds={counter_succeeds}")
        
        return {
            'is_valid_attack': is_valid_attack,
            'original_survives': original_survives,
            'counter_succeeds': counter_succeeds,
            'logical_consistency': logical_consistency,
            'formal_representation': "Non disponible (TweetyProject non disponible)",
            'extensions': {
                'grounded': "Non disponible",
                'complete': ["Non disponible"]
            }
        }
    
    def _fallback_strength_assessment(
        self, 
        original_arg: Argument,
        counter_args: List[CounterArgument]
    ) -> float:
        """
        Méthode de secours pour l'évaluation de la force si TweetyProject n'est pas disponible.
        
        Args:
            original_arg: L'argument original
            counter_args: Liste des contre-arguments
            
        Returns:
            Un score entre 0 et 1 représentant la force de l'argument
        """
        if not counter_args:
            return 1.0
        
        # Compter le nombre de contre-arguments forts et décisifs
        strong_counter_args = sum(1 for ca in counter_args if ca.strength in [ArgumentStrength.STRONG, ArgumentStrength.DECISIVE])
        
        # Calculer un score simple basé sur le nombre et la force des contre-arguments
        total_counter_args = len(counter_args)
        
        # Formule simplifiée: plus il y a de contre-arguments forts, plus le score est bas
        strength_factor = 1.0 - (strong_counter_args / total_counter_args) if total_counter_args > 0 else 1.0
        
        # Réduire encore le score en fonction du nombre total de contre-arguments
        count_factor = max(0.2, 1.0 - (0.1 * total_counter_args))
        
        return strength_factor * count_factor 