import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.mark.real_jpype
class TestJvmStability:
    def test_minimal_jvm_initialization_and_load(self, integration_jvm):
        """
        Teste l'initialisation de la JVM via la fixture integration_jvm
        et une opération JPype minimale (chargement de java.lang.String).
        Ceci vise à isoler les problèmes de stabilité de la JVM dans pytest.
        """
        logger.info("Début de test_minimal_jvm_initialization_and_load.")
        jpype_instance = integration_jvm
        assert jpype_instance is not None, "La fixture integration_jvm n'a pas retourné d'instance JPype."
        
        logger.info("Vérification si la JVM est démarrée...")
        assert jpype_instance.isJVMStarted(), "La JVM devrait être démarrée par integration_jvm."
        logger.info("JVM démarrée avec succès.")

        try:
            logger.info("Tentative de chargement de java.lang.String...")
            StringClass = jpype_instance.JClass("java.lang.String")
            assert StringClass is not None, "java.lang.String n'a pas pu être chargée."
            logger.info("java.lang.String chargée avec succès.")
            
            # Test simple d'utilisation
            java_string = StringClass("Hello from JPype")
            py_string = str(java_string)
            assert py_string == "Hello from JPype", "La conversion de chaîne Java en Python a échoué."
            logger.info(f"Chaîne Java créée et convertie: '{py_string}'")

        except Exception as e:
            logger.error(f"Erreur lors du chargement ou de l'utilisation de java.lang.String: {e}")
            pytest.fail(f"Erreur JPype minimale: {e}")
        
        logger.info("Fin de test_minimal_jvm_initialization_and_load.")