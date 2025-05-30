# tests/integration/conftest.py
import pytest
import jpype
import logging

# Importation prudente de initialize_jvm pour éviter les erreurs si le module n'est pas encore dans le PYTHONPATH
# lors de la collecte des tests par Pytest avant la configuration du pythonpath dans pytest.ini.
# Cependant, pytest.ini configure déjà pythonpath = . argumentation_analysis, donc cela devrait être ok.
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm, LIBS_DIR, TWEETY_VERSION
except ImportError as e:
    # Gérer le cas où le module n'est pas trouvable, par exemple si les tests sont lancés
    # d'une manière qui ne respecte pas le pythonpath configuré.
    # Ou si une dépendance de jvm_setup est manquante au moment de l'import.
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger(__name__).warning(
        f"Impossible d'importer initialize_jvm depuis argumentation_analysis.core.jvm_setup: {e}. "
        "La fixture integration_jvm pourrait ne pas fonctionner correctement. "
        "Assurez-vous que le PYTHONPATH est correctement configuré et que toutes les dépendances sont installées."
    )
    # Définir une fonction factice pour que la fixture ne plante pas à la définition
    def initialize_jvm(*args, **kwargs): # type: ignore
        logging.getLogger(__name__).error(
            "La fonction initialize_jvm factice est appelée. La JVM ne sera PAS initialisée."
        )
        return False
    LIBS_DIR = "libs" # Valeur par défaut factice
    TWEETY_VERSION = "unknown" # Valeur par défaut factice


logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def integration_jvm():
    """
    Fixture de session pour s'assurer que la JVM est initialisée
    avant de lancer les tests d'intégration.
    Utilise la fonction initialize_jvm du projet.
    """
    logger.info("Fixture integration_jvm (session): Tentative d'initialisation de la JVM...")
    if not jpype.isJVMStarted():
        # Utiliser les chemins et versions par défaut définis dans jvm_setup
        # Si des configurations spécifiques sont nécessaires pour l'intégration (par exemple, différents JARs),
        # initialize_jvm devrait être adapté ou une nouvelle fonction de setup JVM
        # spécifique à l'intégration devrait être créée et appelée ici.
        # Pour l'instant, on utilise la configuration standard.
        jvm_ready = initialize_jvm(lib_dir_path=LIBS_DIR, tweety_version=TWEETY_VERSION)
        if not jvm_ready:
            pytest.fail("Échec de l'initialisation de la JVM pour les tests d'intégration. Voir les logs pour détails.", pytrace=False)
        logger.info("Fixture integration_jvm (session): JVM initialisée avec succès.")
    else:
        logger.info("Fixture integration_jvm (session): JVM déjà démarrée.")
    
    # Optionnel: Enregistrer les domaines jpype.imports si ce n'est pas déjà fait par initialize_jvm
    # ou si initialize_jvm n'a pas été appelée car la JVM était déjà démarrée.
    # initialize_jvm le fait déjà, donc redondant ici si elle a été appelée.
    # Mais si la JVM a été démarrée par un autre moyen (ex: un test unitaire précédent qui ne l'arrête pas),
    # il pourrait être utile de s'assurer que les imports sont prêts.
    if jpype.isJVMStarted() and hasattr(jpype, 'imports') and jpype.imports is not None:
        try:
            jpype.imports.registerDomain("org", alias="org")
            jpype.imports.registerDomain("java", alias="java")
            jpype.imports.registerDomain("net", alias="net")
            # Pourrait être utile d'ajouter d'autres domaines de haut niveau si nécessaire
            logger.debug("Fixture integration_jvm (session): Domaines JPype (org, java, net) vérifiés/enregistrés.")
        except Exception as e_reg:
            logger.warning(f"Fixture integration_jvm (session): Avertissement lors de l'enregistrement des domaines JPype: {e_reg}")
            
    return True # Indique que la JVM est (ou devrait être) prête