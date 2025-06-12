import sys
import types
import logging

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE IMPORTS LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

class MockJpypeImports:
    def registerDomain(self, domain, alias=None):
        """Simule jpype.imports.registerDomain()."""
        mock_logger.info(f"jpype.imports.registerDomain('{domain}', alias='{alias}') appelé.")
        # Ne fait rien, car c'est un mock.
        pass

# Crée une instance du mock d'imports. Cette instance sera utilisée pour peupler le module factice.
_the_actual_imports_object = MockJpypeImports()
mock_logger.info("Instance de MockJpypeImports créée (_the_actual_imports_object).")

# Créer un objet module factice pour 'jpype.imports'
# C'est cet objet 'imports_module' qui sera accessible via `from jpype_components import imports`
# ou `jpype.imports` après le patch dans jpype_mock.py principal.
imports_module = types.ModuleType('jpype.imports')
mock_logger.debug(f"Module factice 'jpype.imports' créé: {imports_module}")

# Attribuer les fonctionnalités de notre instance '_the_actual_imports_object' à ce module factice.
if hasattr(_the_actual_imports_object, 'registerDomain'):
    imports_module.registerDomain = _the_actual_imports_object.registerDomain
    mock_logger.debug(f"Fonction 'registerDomain' attachée au module factice 'jpype.imports'.")

# Mettre ce module factice dans sys.modules pour qu'il soit trouvable par 'import jpype.imports'
# Ceci est crucial pour que les imports directs de jpype.imports fonctionnent comme attendu
# après que ce module (jpype_components.imports) soit importé et exécuté.
sys.modules['jpype.imports'] = imports_module
mock_logger.info(f"Module factice 'jpype.imports' injecté dans sys.modules.")

# Exposer le module factice comme 'imports' pour ce fichier,
# afin que `from tests.mocks.jpype_components.imports import imports` fonctionne.
imports = imports_module

mock_logger.info("Module jpype_components.imports initialisé.")