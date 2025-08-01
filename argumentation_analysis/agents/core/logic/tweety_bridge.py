#!/usr/bin/env python
# -*- coding: utf-8 -*-

# FORCE_RELOAD
# argumentation_analysis/agents/core/logic/tweety_bridge.py
"""
Ce module implémente le pont avec la bibliothèque Java TweetyProject en utilisant JPype.

Il est conçu comme un singleton pour garantir qu'une seule instance de la JVM est
démarrée et gérée tout au long de la vie de l'application. Le pont charge les
JARs nécessaires, configure la JVM et expose des handlers pour différentes
logiques (comme la logique propositionnelle ou la logique du premier ordre).

L'initialisation se fait via la méthode `initialize_jvm`.
"""

import jpype
from jpype import java
import jpype.imports
import logging
import os
import glob
import threading
import asyncio
from typing import Optional, Dict, List, Tuple, Any

# Importer les handlers de logique spécifiques
# Pour éviter les dépendances circulaires, on les importe et on les type-hint comme ça
from .pl_handler import PLHandler as PropositionalLogicHandler
from .fol_handler import FOLHandler as FirstOrderLogicHandler
from .af_handler import AFHandler as ArgumentationFrameworkHandler
from .tweety_initializer import TweetyInitializer


logger = logging.getLogger(__name__)

class TweetyBridge:
    """
    Un pont singleton pour interagir avec la bibliothèque Java TweetyProject.
    Gère le cycle de vie de la JVM et fournit un accès aux fonctionnalités logiques.
    """
    _instance = None
    _lock = threading.Lock()
    _jvm_started = False
    _jvm_path: Optional[str] = None
    
    # Handlers pour les différentes logiques. Initialisés avec la logique du pont.
    _pl_handler: Optional[PropositionalLogicHandler] = None
    _af_handler: Optional[ArgumentationFrameworkHandler] = None
    
    # Nouvel attribut pour l'initialiseur
    _initializer: Optional[TweetyInitializer] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TweetyBridge, cls).__new__(cls)
        return cls._instance

    def __init__(self, jar_directory: Optional[str] = None):
        """
        Initialise le pont. La JVM n'est pas démarrée ici, mais dans `initialize_jvm`.
        Les handlers sont chargés paresseusement (lazy-loaded) lors du premier accès.
        """
        if not hasattr(self, '_initialized'):
            self.jar_directory = jar_directory or self._find_default_jar_dir()
            self._initializer = TweetyInitializer(self)
            # L'initialisation de la JVM et des composants est maintenant gérée par une méthode unifiée
            self._initializer.ensure_jvm_and_components_are_ready()
            # Les handlers ne sont plus initialisés ici pour éviter les erreurs de JVM
            self._initialized = True

    def _find_default_jar_dir(self) -> str:
        """
        Trouve le répertoire des JARs par défaut, en supposant une structure de projet standard.
        Le répertoire 'libs/tweety/native' est recherché depuis le répertoire de ce script.
        """
        script_dir = os.path.dirname(__file__)
        # Le chemin relatif vers le répertoire des JARs natifs
        # argumentation_analysis/agents/core/logic/ -> argumentation_analysis/libs/tweety/native
        relative_jar_path = os.path.join(script_dir, '../../../..', 'libs', 'tweety')
        return os.path.normpath(relative_jar_path)

    @classmethod
    def get_instance(cls, jar_directory: Optional[str] = None) -> 'TweetyBridge':
        """
        Méthode d'accès au singleton, avec initialisation si nécessaire.
        """
        if cls._instance is None:
            cls._instance = TweetyBridge(jar_directory)
        return cls._instance

    @property
    def pl_handler(self) -> PropositionalLogicHandler:
        """Retourne le handler pour la logique propositionnelle, en l'initialisant si nécessaire."""
        if not self.initializer.is_jvm_ready():
            raise RuntimeError("La JVM n'est pas démarrée. Appelez initialize_jvm() en premier.")
        if self._pl_handler is None:
            logger.debug("Chargement paresseux (lazy-loading) du PLHandler.")
            self._pl_handler = PropositionalLogicHandler(self._initializer)
        return self._pl_handler

    @property
    def af_handler(self) -> ArgumentationFrameworkHandler:
        """Retourne le handler pour les frameworks d'argumentation, en l'initialisant si nécessaire."""
        if not self.initializer.is_jvm_ready():
            raise RuntimeError("La JVM n'est pas démarrée. Appelez initialize_jvm() en premier.")
        if self._af_handler is None:
            logger.debug("Chargement paresseux (lazy-loading) du AFHandler.")
            self._af_handler = ArgumentationFrameworkHandler(self._initializer)
        return self._af_handler

    @property
    def initializer(self) -> TweetyInitializer:
        """Retourne l'initialiseur Tweety, qui gère le chargement des classes Java."""
        return self._initializer
        

    async def wait_for_jvm(self, timeout: int = 30) -> None:
        """Attend de manière asynchrone que la JVM soit prête."""
        if TweetyInitializer.is_jvm_ready():
            return
        
        waited_time = 0
        while not TweetyInitializer.is_jvm_ready() and waited_time < timeout:
            await asyncio.sleep(0.5)
            waited_time += 0.5

        if not TweetyInitializer.is_jvm_ready():
            raise TimeoutError(f"La JVM n'a pas démarré dans le temps imparti de {timeout} secondes.")

    def set_jvm_path(self, jvm_path: str):
        """Définit manuellement le chemin vers la bibliothèque de la JVM (dll, so, etc.)."""
        self._jvm_path = jvm_path
        logger.info(f"Chemin de la JVM défini manuellement sur : {jvm_path}")

    def initialize_jvm(self, jvm_path: Optional[str] = None) -> None:
        """
        Démarre la JVM avec les JARs du répertoire spécifié.
        Cette méthode est bloquante et peut prendre du temps.
        """
        with self._lock:  # Utilise un verrou pour éviter le démarrage concurrent de la JVM
            if TweetyInitializer.is_jvm_ready():
                logger.warning("La JVM est déjà démarrée. L'appel d'initialisation est ignoré.")
                return

            effective_jvm_path = jvm_path or self._jvm_path or jpype.getDefaultJVMPath()
            logger.info(f"Tentative de démarrage de la JVM avec le chemin : {effective_jvm_path}")

            try:
                jar_paths = glob.glob(os.path.join(self.jar_directory, '*.jar'))
                if not jar_paths:
                    raise IOError(f"Aucun fichier .jar trouvé dans le répertoire : {self.jar_directory}")

                classpath = os.pathsep.join(jar_paths)
                logger.info(f"Classpath configuré avec {len(jar_paths)} JARs.")
                
                jpype.startJVM(
                    effective_jvm_path,
                    "-ea",  # Enable assertions
                    f"-Djava.class.path={classpath}",
                    convertStrings=False
                )
                TweetyBridge._jvm_started = True
                logger.info("La JVM a démarré avec succès.")
                
                # Une fois la JVM démarrée, on peut charger les classes
                self._initializer.import_java_classes()
                
            except (Exception, jpype.JException) as e:
                logger.error(f"Échec du démarrage de la JVM avec le chemin '{effective_jvm_path}'. Erreur : {e}", exc_info=True)
                TweetyBridge._jvm_started = False
                # Propage l'exception pour que les appelants sachent que l'initialisation a échoué.
                raise RuntimeError("Échec de l'initialisation de la JVM.") from e

    def shutdown_jvm(self):
        """Arrête la JVM si elle est en cours d'exécution."""
        with self._lock:
            if TweetyInitializer.is_jvm_ready():
                # shutdown_jvm est maintenant géré de manière centralisée
                from argumentation_analysis.core.jvm_setup import shutdown_jvm
                shutdown_jvm()
                self._jvm_started = False
                logger.info("La JVM a été arrêtée via le gestionnaire centralisé.")

    def validate_pl_formula(self, formula: str) -> bool:
        """Valide la syntaxe d'une formule de logique propositionnelle en tentant de la parser."""
        try:
            # La validation se fait en tentant un parsing. Si ça ne lève pas d'erreur, c'est valide.
            self.pl_handler.parse_pl_formula(formula)
            return True
        except ValueError:
            return False

    def pl_query(self, knowledge_base: str, query: str) -> Optional[bool]:
        """
        Exécute une requête en logique propositionnelle.
        Retourne True si la KB entraîne la requête, False sinon, ou None en cas d'erreur.
        """
        return self.pl_handler.pl_query(knowledge_base, query)

    def create_pl_belief_base_from_string(self, formula_string: str) -> Optional["java.lang.Object"]:
        """Crée un objet PlBeliefSet Java à partir d'une chaîne."""
        return self.pl_handler.create_belief_base_from_string(formula_string)


    @staticmethod
    def get_tweety_project_version() -> str:
        """
        Récupère la version de TweetyProject à partir du nom d'un des fichiers JAR.
        Suppose un format de nommage comme 'tweetyproject-1.2.3.jar'.
        """
        bridge = TweetyBridge.get_instance()
        try:
            jar_paths = glob.glob(os.path.join(bridge.jar_directory, 'tweetyproject-*.jar'))
            if jar_paths:
                filename = os.path.basename(jar_paths[0])
                # Extrait la version, par ex. de 'tweetyproject-2.0.jar'
                version = filename.replace('tweetyproject-', '').replace('.jar', '')
                return version
        except Exception as e:
            logger.warning(f"Impossible d'extraire la version de TweetyProject : {e}")
        return "Version inconnue"