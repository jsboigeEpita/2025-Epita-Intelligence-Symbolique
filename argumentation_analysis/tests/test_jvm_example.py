"""
Exemple de test utilisant la classe JVMTestCase.

Ce test montre comment utiliser la classe JVMTestCase pour créer des tests
qui dépendent de la JVM. Il sera automatiquement sauté si la JVM n'est pas
disponible ou si les JARs nécessaires ne sont pas présents.
"""

import logging
from argumentation_analysis.tests.jvm_test_case import JVMTestCase

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
        self.assertTrue(jpype.isJVMStarted(), "La JVM devrait être démarrée")
        
        # Vérifier que les domaines sont enregistrés
        self.assertTrue(hasattr(jpype.imports, "registerDomain"), "La méthode registerDomain devrait être disponible")
        
        # Afficher des informations sur la JVM
        logging.info(f"JVM Version: {jpype.getJVMVersion()}")
        logging.info(f"JVM Path: {jpype.getJVMPath()}")
    
    def test_tweety_jars_loaded(self):
        """Teste si les JARs Tweety sont correctement chargés."""
        # Ce test sera sauté si la JVM n'est pas disponible
        import jpype
        
        # Essayer d'importer une classe de Tweety
        try:
            # Importer une classe du module logics.pl
            from org.tweetyproject.logics.pl.syntax import Proposition
            
            # Créer une proposition
            p = Proposition("p")
            
            # Vérifier que la proposition est correctement créée
            self.assertEqual("p", p.getName(), "Le nom de la proposition devrait être 'p'")
            self.assertEqual("p", str(p), "La représentation en chaîne de la proposition devrait être 'p'")
            
            logging.info(f"Proposition créée avec succès: {p}")
        except Exception as e:
            self.fail(f"Impossible d'importer ou d'utiliser la classe Proposition: {e}")