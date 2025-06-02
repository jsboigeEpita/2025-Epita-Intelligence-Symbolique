# -*- coding: utf-8 -*-
"""
Exemple de test utilisant la classe JVMTestCase.

Ce test montre comment utiliser la classe JVMTestCase pour créer des tests
qui dépendent de la JVM. Il sera automatiquement sauté si la JVM n'est pas
disponible ou si les JARs nécessaires ne sont pas présents.
"""

import logging
import pytest # Ajout de l'import pytest
from argumentation_analysis.tests.jvm_test_case import JVMTestCase
import sys # Pour vérifier le module importé

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

class TestJVMExample(JVMTestCase):
    """Exemple de test utilisant la classe JVMTestCase."""
    
    def test_jvm_initialized(self):
        """Teste si la JVM est correctement initialisée."""
        # Ce test sera sauté si la JVM n'est pas disponible
        import jpype
        self.assertTrue(jpype.isJVMStarted(), "La JVM devrait être démarrée par JVMTestCase ou conftest.py")
        logging.info(f"Module jpype utilisé: {getattr(jpype, '__file__', 'N/A')}")
        
        # Vérifier que les domaines sont enregistrés
        self.assertTrue(hasattr(jpype.imports, "registerDomain"), "La méthode registerDomain devrait être disponible sur jpype.imports")
        
        # Afficher des informations sur la JVM
        logging.info(f"JVM Version: {jpype.getJVMVersion()}")
        try:
            # Utilisation de jpype.config.jvm_path pour obtenir le chemin de la JVM
            # car jpype.getJVMPath() n'existe pas dans JPype 1.5.2.
            jvm_path = jpype.config.jvm_path
            if jvm_path:
                logging.info(f"JVM Path (jpype.config.jvm_path): {jvm_path}")
            else:
                # Si jpype.config.jvm_path est None, JPype utilise le JAVA_HOME ou une détection interne.
                # jpype.getDefaultJVMPath() pourrait être appelé ici mais il est plus pertinent avant startJVM.
                logging.info(f"JVM Path: Non explicitement configuré via jpype.config.jvm_path (probablement via JAVA_HOME ou détection interne). Default JVM path avant démarrage: {jpype.getDefaultJVMPath()}")
        except AttributeError:
             # jpype.config.jvm_path n'est pas disponible, cela peut arriver si la JVM n'est pas encore initialisée par JPype ou si la version est différente.
             # Tentative avec jpype.getDefaultJVMPath() comme fallback, bien que ce soit typiquement pour avant le démarrage.
            try:
                default_jvm_path = jpype.getDefaultJVMPath()
                logging.info(f"jpype.config.jvm_path non disponible. JVM Path (jpype.getDefaultJVMPath()): {default_jvm_path}")
            except Exception as e_default:
                logging.warning(f"Impossible de récupérer le chemin JVM via jpype.config.jvm_path ou jpype.getDefaultJVMPath(): {e_default}")
        except Exception as e:
            logging.warning(f"Impossible de récupérer le chemin JVM via jpype.config.jvm_path: {e}")
    
    def test_tweety_jars_loaded(self):
        """Teste si les JARs Tweety sont correctement chargés."""
        # Ce test sera sauté si la JVM n'est pas disponible
        logging.info("test_tweety_jars_loaded: Début du test")
        
        import jpype # Assurer que jpype est dans la portée locale de la fonction
        self.assertTrue(jpype.isJVMStarted(), "La JVM devrait être démarrée.")
        logging.info(f"test_tweety_jars_loaded: Module jpype utilisé: {getattr(jpype, '__file__', 'N/A')}")
        
        # Essayer d'importer une classe de Tweety
        try:
            logging.info("test_tweety_jars_loaded: Avant from org.tweetyproject.logics.pl.syntax import Proposition")
            # Importer une classe du module logics.pl
            from org.tweetyproject.logics.pl.syntax import Proposition
            logging.info(f"test_tweety_jars_loaded: Après import Proposition. Proposition: {Proposition}")
            
            logging.info("test_tweety_jars_loaded: Avant p = Proposition(\"p\")")
            # Créer une proposition
            p = Proposition("p")
            logging.info(f"test_tweety_jars_loaded: Après p = Proposition(\"p\"). p: {p}")
            
            # Vérifier que la proposition est correctement créée
            logging.info("test_tweety_jars_loaded: Avant p.getName()")
            name = p.getName()
            logging.info(f"test_tweety_jars_loaded: Après p.getName(). name: {name}")
            self.assertEqual("p", name, "Le nom de la proposition devrait être 'p'")
            
            logging.info("test_tweety_jars_loaded: Avant str(p)")
            str_p = str(p)
            logging.info(f"test_tweety_jars_loaded: Après str(p). str_p: {str_p}")
            self.assertEqual("p", str_p, "La représentation en chaîne de la proposition devrait être 'p'")
            
            logging.info(f"Proposition créée avec succès: {p}")
        except Exception as e:
            logging.error(f"test_tweety_jars_loaded: Exception attrapée: {e}", exc_info=True)
            self.fail(f"Impossible d'importer ou d'utiliser la classe Proposition: {e}")