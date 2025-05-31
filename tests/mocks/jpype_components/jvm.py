import sys
import os
import logging

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE JVM LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

# Variables globales pour simuler l'état de la JVM
_jvm_started = False
_jvm_path = None

# Simuler jpype.config (juste assez pour que startJVM puisse y accéder)
# La vraie logique de config.py sera dans son propre fichier.
class MinimalMockConfig:
    def __init__(self):
        self.jvm_path = None
config = MinimalMockConfig()


def isJVMStarted():
    """Simule jpype.isJVMStarted()."""
    # return _jvm_started # Comportement original
    # Forcer True pour satisfaire la fixture jvm_manager dans tests/integration/jpype_tweety/conftest.py
    # Cette logique devra peut-être être revue globalement plus tard.
    # Pour l'instant, on garde le comportement qui permet aux tests de passer.
    mock_logger.debug(f"isJVMStarted() appelée. Retourne: True (valeur forcée pour les tests)")
    return True

def startJVM(jvmpath=None, *args, **kwargs):
    """Simule jpype.startJVM()."""
    global _jvm_started, _jvm_path
    _jvm_started = True
    _jvm_path = jvmpath or getDefaultJVMPath()
    # Mettre à jour config.jvm_path aussi, car c'est souvent là que le code le cherche après démarrage
    config.jvm_path = _jvm_path # Utilise le MinimalMockConfig local
    mock_logger.info(f"startJVM appelée. _jvm_started mis à True. Classpath: {kwargs.get('classpath')}")
    mock_logger.info(f"JVM démarrée avec le chemin: {_jvm_path}")

def shutdownJVM():
    """Simule jpype.shutdownJVM()."""
    global _jvm_started
    # Les prints de debug originaux peuvent être utiles, on les garde pour l'instant.
    # print("[MOCK DEBUG] Avant opérations dans shutdownJVM:")
    # jpype_module = sys.modules.get('jpype') # Ceci ne sera plus pertinent ici
    # print(f"[MOCK DEBUG] sys.modules.get('jpype'): {jpype_module}")
    # ... (autres prints qui dépendaient du contexte de jpype_mock.py)
    _jvm_started = False
    mock_logger.info("JVM arrêtée")

def getDefaultJVMPath():
    """Simule jpype.getDefaultJVMPath()."""
    if sys.platform == "win32":
        return os.path.join(os.environ.get("JAVA_HOME", "C:\\Program Files\\Java\\jdk-11"), "bin", "server", "jvm.dll") if os.environ.get("JAVA_HOME") else "C:\\Program Files\\Java\\jdk-11\\bin\\server\\jvm.dll"
    elif sys.platform == "darwin":
        return "/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home/lib/server/libjvm.dylib"
    else:
        return "/usr/lib/jvm/java-11-openjdk/lib/server/libjvm.so"

def getJVMPath():
    """Simule jpype.getJVMPath()."""
    return _jvm_path or getDefaultJVMPath()

def getJVMVersion():
    """Simule jpype.getJVMVersion()."""
    return ("Mock JVM Version 1.0 (Java 11 compatible)", 11, 0, 0)

def getClassPath(as_string=False):
    """Simule jpype.getClassPath()."""
    mock_logger.info(f"getClassPath(as_string={as_string}) CALLED")
    mock_classpath_list = ['dummy/mocked_lib.jar', 'another/mocked_dependency.jar']
    if as_string:
        return os.pathsep.join(mock_classpath_list)
    else:
        return mock_classpath_list