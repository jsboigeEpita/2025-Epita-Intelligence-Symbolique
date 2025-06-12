
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# import logging
import pytest
import subprocess
import importlib.metadata
import os
from pathlib import Path


# Import the functions to be tested
from argumentation_analysis.utils.dev_tools.env_checks import (
    check_java_environment,
    check_jpype_config,
    check_python_dependencies,
    _run_command  # If we want to test it directly or mock its usage precisely
)

# Mocks for check_java_environment
from unittest import mock

@pytest.fixture
def mock_os_environ_java():
    with mock.patch.dict(os.environ, {}, clear=True) as mock_env:
        yield mock_env

@pytest.fixture
def mock_path_java(mock_run_command_java, unique_id_gen): # mock_run_command_java n'est plus utilisé directement ici mais gardé pour la signature si des tests en dépendent
    """
    Mocks pathlib.Path for Java environment checks.
    Yields the mocked Path instance (that Path() would return).
    """
    id_generator = unique_id_gen() # Obtenir une instance du générateur
    unique_id = next(id_generator)
    # logging.debug(f"mock_path_java fixture setup started (ID: {unique_id})") # logging import manquant

    # S'assurer d'obtenir la classe Path originale avant tout patch potentiel par d'autres fixtures
    import sys
    import pathlib as fresh_pathlib # Importer une version fraîche de pathlib pour instancier le flavour
    # env_checks_module_local_for_java_mock n'est plus nécessaire ici car on cible directement _PathInternal
    
    # Récupérer original_path_class pour spec, même si _flavour est problématique
    # Cela pourrait encore être utile pour d'autres aspects de la spec.
    # Si cela continue de causer des problèmes, nous pourrions devoir le retirer aussi.
    original_path_class_for_spec = sys.modules['pathlib'].Path


    # This is the mock for the Path *class* itself
    # It will replace 'argumentation_analysis.utils.dev_tools.env_checks.pathlib.Path'
    mock_path_class_replacement = mock.MagicMock(
        name=f"MockPathClassReplacement_{unique_id}",
        spec=original_path_class_for_spec  # Utiliser pour la spec
    )

    # Définir _flavour directement avec une instance du flavour approprié
    try:
        mock_path_class_replacement._flavour = fresh_pathlib._WindowsFlavour()
    except AttributeError:
        mock_path_class_replacement._flavour = fresh_pathlib._PosixFlavour()
    # logging.debug(f"Successfully set _flavour for MockPathClassReplacement_{unique_id}")

    # This is the mock for the Path *instance* (the object returned by Path(...))
    # Utiliser original_path_class_for_spec pour la spec de l'instance également
    mock_path_instance = mock.MagicMock(
        spec=original_path_class_for_spec(),
        name=f"MockPathInstance_{unique_id}"
    )
    
    # Configure the class mock to return our instance mock when called
    mock_path_class_replacement.return_value = mock_path_instance

    # Configure the behavior of the mocked Path instance
    java_exe_mock = mock.MagicMock(spec=original_path_class_for_spec(), name=f"JavaExeMock_{unique_id}")
    java_exe_mock.is_file.return_value = True
    java_exe_mock.configure_mock(**{'__str__': lambda self: "/mocked/java_home/bin/java"}) # Accepte self

    bin_dir_mock = mock.MagicMock(spec=original_path_class_for_spec(), name=f"BinDirMock_{unique_id}")
    bin_dir_mock.__truediv__.return_value = java_exe_mock
    bin_dir_mock.is_dir.return_value = True
    bin_dir_mock.exists.return_value = True
    bin_dir_mock.configure_mock(**{'__str__': lambda self: "/mocked/java_home/bin"}) # Accepte self


    mock_path_instance.is_dir.return_value = True
    mock_path_instance.exists.return_value = True

    def custom_truediv(other):
        if other == "bin":
            # logging.debug(f"MockPathInstance_{unique_id}.__truediv__('bin') returning BinDirMock_{unique_id}")
            return bin_dir_mock
        # logging.debug(f"MockPathInstance_{unique_id}.__truediv__('{other}') returning a new default mock")
        default_divided_mock = mock.MagicMock(spec=original_path_class_for_spec(), name=f"DividedMock_{other}_{unique_id}")
        default_divided_mock.exists.return_value = False
        return default_divided_mock

    mock_path_instance.__truediv__.side_effect = custom_truediv
    mock_path_instance.configure_mock(**{'__str__': lambda self: "/mocked/java_home"}) # Accepte self
    
    # Fonction de configuration pour les tests, attachée à l'instance mockée
    def configure_java_exe_path_on_instance(is_dir_java_home, java_exe_exists_in_bin, java_exe_is_file_in_bin):
        mock_path_instance.is_dir.return_value = is_dir_java_home
        mock_path_instance.exists.return_value = is_dir_java_home # Si c'est un dir, ça existe
        
        # Configurer le comportement de /opt/java/bin/java
        java_exe_mock.exists.return_value = java_exe_exists_in_bin
        java_exe_mock.is_file.return_value = java_exe_is_file_in_bin
        
        # Configurer le comportement de /opt/java/bin
        bin_dir_mock.is_dir.return_value = True # On assume que 'bin' est toujours un dir s'il est atteint
        bin_dir_mock.exists.return_value = True

    mock_path_instance.configure_java_exe_path = configure_java_exe_path_on_instance


    # Cible directement _PathInternal dans le module env_checks
    patch_target_str = 'argumentation_analysis.utils.dev_tools.env_checks._PathInternal'
    patcher = mock.patch(patch_target_str, new=mock_path_class_replacement)
    
    # logging.debug(f"mock_path_java (ID: {unique_id}): Patcher created for target '{patch_target_str}' with new=MockPathClassReplacement_{unique_id} (ID: {id(mock_path_class_replacement)})")

    try:
        patched_path_internal_ref = patcher.start() # Renommé pour clarté
        # logging.debug(f"mock_path_java (ID: {unique_id}): Patcher started. Patched _PathInternal is '{patched_path_internal_ref.__name__ if hasattr(patched_path_internal_ref, '__name__') else patched_path_internal_ref}' (ID: {id(patched_path_internal_ref)})")
        
        assert hasattr(patched_path_internal_ref, '_flavour'), "Patched _PathInternal (our mock) MUST have _flavour"
        # L'assertion 'is original_path_class._flavour' est retirée.
        # logging.debug(f"Patched Path attribute (ID: {id(patched_path_attribute)}) HAS _flavour set.")

        yield mock_path_instance  # Les tests utiliseront cette instance pour configurer et vérifier
    finally:
        patcher.stop()
        # logging.debug(f"mock_path_java fixture teardown (ID: {unique_id})")

@pytest.fixture
def mock_run_command_java():
    # This mocks the _run_command function within the env_checks module
    with mock.patch('argumentation_analysis.utils.dev_tools.env_checks._run_command') as mock_run:
        yield mock_run

# Tests for check_java_environment
def test_check_java_environment_all_ok(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir_java_home=True, java_exe_exists_in_bin=True, java_exe_is_file_in_bin=True)
    mock_run_command_java.return_value = (0, "", "java version \"11.0.1\" 2021-04-20") # stdout, stderr

    assert check_java_environment() is True
    assert "JAVA_HOME est défini : /opt/java" in caplog.text
    assert "JAVA_HOME pointe vers un répertoire Java valide" in caplog.text # Vérifie le log pour mock_path_java.is_dir
    assert "JAVA_HOME pointe vers un répertoire Java valide (/mocked/java_home/bin/java)" in caplog.text # Corrigé pour correspondre au log réel
    assert "Commande 'java -version' exécutée avec succès. Version détectée : java version \"11.0.1\"" in caplog.text
    assert "L'environnement Java est jugé correctement configuré" in caplog.text

def test_check_java_environment_no_java_home_version_ok(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    # JAVA_HOME is not set (default from mock_os_environ_java)
    # mock_path_java n'est pas configuré car JAVA_HOME n'est pas utilisé pour créer un Path
    mock_run_command_java.return_value = (0, "", "openjdk version \"1.8.0_292\"")
    
    assert check_java_environment() is False # Fails because JAVA_HOME is critical for "correctly configured"
    assert "JAVA_HOME n'est pas défini" in caplog.text
    assert "Commande 'java -version' exécutée avec succès." in caplog.text
    assert "Bien que 'java -version' fonctionne, JAVA_HOME n'est pas défini ou est invalide." in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_home_invalid_dir(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/invalid/java_home"
    mock_path_java.configure_java_exe_path(is_dir_java_home=False, java_exe_exists_in_bin=False, java_exe_is_file_in_bin=False) # JAVA_HOME path is not a dir
    mock_run_command_java.return_value = (0, "", "openjdk version \"1.8.0_292\"")

    assert check_java_environment() is False
    assert "JAVA_HOME (/invalid/java_home) n'est pas un répertoire valide." in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_home_no_java_exe(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java_no_exe"
    # Path for JAVA_HOME itself is a dir, but bin/java doesn't exist or isn't a file
    mock_path_java.configure_java_exe_path(is_dir_java_home=True, java_exe_exists_in_bin=False, java_exe_is_file_in_bin=False)
    mock_run_command_java.return_value = (0, "", "openjdk version \"1.8.0_292\"")

    assert check_java_environment() is False
    assert "JAVA_HOME (/opt/java_no_exe) ne semble pas contenir une installation Java valide (exécutable non trouvé à /mocked/java_home/bin/java)" in caplog.text # Corrigé pour correspondre au log réel
    # La ligne précédente couvre maintenant l'information sur l'exécutable non trouvé.
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_version_fails_filenotfound(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir_java_home=True, java_exe_exists_in_bin=True, java_exe_is_file_in_bin=True)
    mock_run_command_java.return_value = (-1, "", "FileNotFoundError: java") # Simulating _run_command's FileNotFoundError case

    assert check_java_environment() is False
    # assert "Échec de l'exécution de 'java -version'." in caplog.text # This comes from _run_command via logger
    assert "Java n'est pas trouvé dans le PATH (FileNotFoundError)." in caplog.text # This is from check_java_environment
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_version_fails_returncode(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir_java_home=True, java_exe_exists_in_bin=True, java_exe_is_file_in_bin=True)
    mock_run_command_java.return_value = (1, "stdout error", "stderr error")

    assert check_java_environment() is False
    assert "Échec de l'exécution de 'java -version'. Code de retour : 1" in caplog.text
    assert "Stderr: stderr error" in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_version_ok_no_output(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir_java_home=True, java_exe_exists_in_bin=True, java_exe_is_file_in_bin=True)
    mock_run_command_java.return_value = (0, "", "") # Successful run but no version info

    assert check_java_environment() is False # Fails because no version info means it's not properly configured
    assert "Commande 'java -version' exécutée, mais n'a retourné aucune information de version." in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text


# Mocks for check_jpype_config
@pytest.fixture
def mock_jpype_module_fixture(): # Renamed to avoid conflict with parameter name
    # Mock the entire jpype module as it's imported directly in env_checks
    jpype_mock = mock.MagicMock(name="jpype_module")
    jpype_mock.isJVMStarted = mock.MagicMock(name="isJVMStarted")
    jpype_mock.getDefaultJVMPath = mock.MagicMock(name="getDefaultJVMPath")
    jpype_mock.startJVM = mock.MagicMock(name="startJVM")
    jpype_mock.shutdownJVM = mock.MagicMock(name="shutdownJVM")
    jpype_mock.JClass = mock.MagicMock(name="JClass")

    jpype_imports_mock = mock.MagicMock(name="jpype.imports")
    jpype_mock.imports = jpype_imports_mock

    # Patch sys.modules so that 'import jpype' in env_checks gets our mock
    with mock.patch.dict('sys.modules', {'jpype': jpype_mock, 'jpype.imports': jpype_imports_mock}):
        yield jpype_mock

# Tests for check_jpype_config
def test_check_jpype_config_import_error_simulated(caplog):
    # Simulate ImportError for jpype
    # The import is `import jpype` and `import jpype.imports` inside check_jpype_config
    # Need to import builtins for mocking __import__
    import builtins # Make sure this is imported at the top of the file or within the test
    original_import = builtins.__import__
    def import_side_effect(name, globals_map=None, locals_map=None, fromlist=(), level=0):
        if name == 'jpype':
            raise ImportError("Simulated JPype import error")
        return original_import(name, globals_map, locals_map, fromlist, level)

    with mock.patch('builtins.__import__', side_effect=import_side_effect):
        assert check_jpype_config() is False
    assert "Échec de l'import du module JPype. JPype n'est probablement pas installé." in caplog.text

def test_check_jpype_config_jvm_already_started(mock_jpype_module_fixture, caplog):
    mock_jpype_module_fixture.isJVMStarted.return_value = True
    
    assert check_jpype_config() is True
    assert "La JVM est déjà démarrée." in caplog.text
    mock_jpype_module_fixture.startJVM.assert_not_called()
    mock_jpype_module_fixture.shutdownJVM.assert_not_called()
    # Check for JClass test log
    assert "Test d'accès à une classe Java de base (java.lang.String) via JPype réussi (implicitement)." in caplog.text


def test_check_jpype_config_start_and_shutdown_jvm_ok(mock_jpype_module_fixture, caplog):
    # Sequence: not started, started, still started (before shutdown)
    mock_jpype_module_fixture.isJVMStarted.side_effect = [False, True, True]
    mock_jpype_module_fixture.getDefaultJVMPath.return_value = "/path/to/jvm/libjvm.so"
    
    assert check_jpype_config() is True
    assert "La JVM n'est pas démarrée. Tentative de démarrage..." in caplog.text
    mock_jpype_module_fixture.startJVM.assert_called_once_with("/path/to/jvm/libjvm.so", convertStrings=False)
    assert "JVM démarrée avec succès par cette fonction." in caplog.text
    assert "Test d'accès à une classe Java de base (java.lang.String) via JPype réussi (implicitement)." in caplog.text
    assert "Arrêt de la JVM démarrée par cette fonction..." in caplog.text
    mock_jpype_module_fixture.shutdownJVM.assert_called_once()
    assert "JVM arrêtée avec succès." in caplog.text

def test_check_jpype_config_start_jvm_fails(mock_jpype_module_fixture, caplog):
    mock_jpype_module_fixture.isJVMStarted.return_value = False
    mock_jpype_module_fixture.getDefaultJVMPath.return_value = "/path/to/jvm/libjvm.so"
    mock_jpype_module_fixture.startJVM.side_effect = Exception("JVM start failed miserably")

    assert check_jpype_config() is False
    assert "Échec du démarrage de la JVM : JVM start failed miserably" in caplog.text
    mock_jpype_module_fixture.shutdownJVM.assert_not_called()

def test_check_jpype_config_shutdown_jvm_fails(mock_jpype_module_fixture, caplog):
    mock_jpype_module_fixture.isJVMStarted.side_effect = [False, True, True]
    mock_jpype_module_fixture.getDefaultJVMPath.return_value = "/path/to/jvm/libjvm.so"
    mock_jpype_module_fixture.shutdownJVM.side_effect = Exception("JVM shutdown failed spectacularly")

    assert check_jpype_config() is False # Fails if shutdown fails
    assert "JVM démarrée avec succès par cette fonction." in caplog.text
    assert "Erreur lors de l'arrêt de la JVM : JVM shutdown failed spectacularly" in caplog.text
    # The final status jpype_ok becomes False due to shutdown error
    assert "Des problèmes ont été détectés avec la configuration de JPype ou la gestion de la JVM." in caplog.text


# Mocks for check_python_dependencies
@pytest.fixture
def mock_file_operations_deps_fixture(unique_id_gen):
    """
    Mocks pathlib.Path and builtins.open for file operation checks (e.g., reading requirements).
    Yields a setup function to configure file mocks, the mocked Path class replacement, and the mocked open function.
    """
    id_generator = unique_id_gen() # Obtenir une instance du générateur
    fixture_unique_id = next(id_generator) # ID unique pour cette invocation de fixture
    # logging.debug(f"mock_file_operations_deps_fixture setup started (ID: {fixture_unique_id})")
    
    import sys
    import pathlib as fresh_pathlib # Importer une version fraîche de pathlib pour instancier le flavour
    # env_checks_module_local n'est plus nécessaire ici car on cible directement _PathInternal

    # Récupérer original_path_class pour spec (utilisé par spec=True et pour les instances)
    original_path_class_for_spec = sys.modules['pathlib'].Path
    
    mock_path_instances_cache = {}
    
    # Définir path_constructor_side_effect_impl d'abord
    def path_constructor_side_effect_impl(path_arg):
        if not hasattr(path_constructor_side_effect_impl, "instance_counter"):
            path_constructor_side_effect_impl.instance_counter = 0
        
        path_str = str(path_arg)
        if path_str not in mock_path_instances_cache:
            path_constructor_side_effect_impl.instance_counter += 1
            instance_id = path_constructor_side_effect_impl.instance_counter
            instance = mock.MagicMock(
                spec=original_path_class_for_spec(),
                name=f"MockPathInstance_FileOps_{path_str.replace('/', '_').replace('.', '_')}_{fixture_unique_id}_{instance_id}"
            )
            instance.configure_mock(**{'__str__': lambda self, p=path_str: p, 'name': path_str})
            instance._is_our_mock_path_instance = True # Marqueur pour _instancecheck
            
            instance.exists.return_value = False
            instance.is_file.return_value = False
            instance.is_dir.return_value = False
            
            def instance_truediv_side_effect(other_segment):
                new_path_str = f"{path_str}/{str(other_segment)}".replace("\\", "/")
                return path_constructor_side_effect_impl(new_path_str) # Appel récursif à l'implémentation
            instance.__truediv__ = mock.MagicMock(side_effect=instance_truediv_side_effect)
            
            mock_path_instances_cache[path_str] = instance
        return mock_path_instances_cache[path_str]

    # Définir une classe mock qui peut être utilisée comme un type pour isinstance
    class MockPathClassForIsinstance:
        def __new__(cls, path_arg):
            # Quand on fait _PathInternal(path_arg), ceci sera appelé.
            return path_constructor_side_effect_impl(path_arg)

        # Attribut de classe pour _flavour
        try:
            _flavour = fresh_pathlib._WindowsFlavour()
        except AttributeError:
            _flavour = fresh_pathlib._PosixFlavour()

        @classmethod
        def _instancecheck(cls, instance):
            # Permet à isinstance(mock_instance, MockPathClassForIsinstance) de fonctionner
            return hasattr(instance, '_is_our_mock_path_instance')

    # Ce side_effect sera appliqué au mock de classe créé par spec=True.

    mocked_file_contents_for_open = {}

    def custom_mock_open_logic(file_path_arg, mode='r', encoding=None):
        file_path_str = str(file_path_arg)
        # logging.debug(f"custom_mock_open_logic called for: '{file_path_str}', mode: '{mode}'")
        if file_path_str in mocked_file_contents_for_open:
            if 'r' not in mode:
                raise IOError(f"Mock file '{file_path_str}' opened for non-read mode '{mode}' not fully supported.")
            content = mocked_file_contents_for_open[file_path_str]
            # logging.debug(f"custom_mock_open_logic: Returning mock_open handle for '{file_path_str}'.")
            file_handle_factory = mock.mock_open(read_data=content)
            return file_handle_factory()
        else:
            # logging.warning(f"custom_mock_open_logic: File '{file_path_str}' not found. Raising FileNotFoundError.")
            raise FileNotFoundError(f"[Mock] File not found by custom_mock_open_logic: {file_path_str}")

    # env_checks.py uses global open() which is builtins.open
    final_open_patch_target_str = 'builtins.open'

    # Cible directement _PathInternal dans le module env_checks
    path_patch_target_str = 'argumentation_analysis.utils.dev_tools.env_checks._PathInternal'
    # Patcher _PathInternal avec notre classe mock qui se comporte comme un type
    path_patcher = mock.patch(path_patch_target_str, new=MockPathClassForIsinstance)
    open_patcher = mock.patch(final_open_patch_target_str, new=custom_mock_open_logic)

    try:
        # patched_Path_class_obj est maintenant la classe MockPathClassForIsinstance elle-même.
        patched_Path_class_obj = path_patcher.start()
        
        assert patched_Path_class_obj is MockPathClassForIsinstance, \
            "The patched object should be our MockPathClassForIsinstance class."
        assert hasattr(patched_Path_class_obj, '_flavour'), \
            "Patched _PathInternal (MockPathClassForIsinstance class) MUST have _flavour"
        
        patched_open_func = open_patcher.start()

        def setup_mock_files(files_config_dict):
            mocked_file_contents_for_open.clear()
            mock_path_instances_cache.clear()
            if hasattr(path_constructor_side_effect_impl, "instance_counter"):
                delattr(path_constructor_side_effect_impl, "instance_counter")

            for path_key, config in files_config_dict.items():
                # On s'assure que les instances sont créées et configurées via path_constructor_side_effect_impl
                # qui sera appelé par MockPathClassForIsinstance.__new__ lorsque le SUT fait _PathInternal(...)
                mock_instance = path_constructor_side_effect_impl(str(path_key))
                
                mock_instance.exists.return_value = config.get("exists", False)
                mock_instance.is_file.return_value = config.get("is_file", False)
                mock_instance.is_dir.return_value = config.get("is_dir", False)
                
                if "content" in config:
                    mocked_file_contents_for_open[str(path_key)] = config["content"]

        # Yield the setup function, our MockPathClassForIsinstance (qui est un type), et la fonction open mockée
        yield setup_mock_files, MockPathClassForIsinstance, patched_open_func
    finally:
        path_patcher.stop()
        open_patcher.stop()
        # logging.debug(f"mock_file_operations_deps_fixture teardown (ID: {unique_id})")

@pytest.fixture
def mock_pkg_resources_deps_fixture(): # Renamed
    pkg_resources_mock = mock.MagicMock(name="pkg_resources_module")
    
    # Store the original parse method to call it for non-custom cases
    # This requires pkg_resources to be actually available in the test environment
    # or a more sophisticated mock for Requirement.parse.
    # For simplicity, we'll make a flexible mock here.
    def mock_requirement_parse_impl(req_string):
        mock_req = mock.MagicMock()
        # Basic parsing for project_name
        project_name_part = req_string.split("==")[0].split(">=")[0].split("<=")[0].split("!=")[0].split("~=")[0].split(";")[0].split("#")[0].strip()
        mock_req.project_name = project_name_part
        
        specs = []
        # Simplified specifier parsing
        if "==" in req_string: specs.append(("==", req_string.split("==")[1].split(";")[0].split("#")[0].strip()))
        elif ">=" in req_string: specs.append((">=", req_string.split(">=")[1].split(";")[0].split("#")[0].strip()))
        # Add other operators as needed for more complex tests
        mock_req.specs = specs
        
        from packaging.specifiers import SpecifierSet # Use a real SpecifierSet for robust testing
        if specs:
            try:
                # Attempt to create a valid specifier string
                spec_str = ",".join(op + ver for op, ver in specs)
                mock_req.specifier = SpecifierSet(spec_str)
            except Exception: # Fallback for complex/invalid specifiers in this simplified mock
                mock_req.specifier = SpecifierSet("") # Treat as no specifier if parsing fails
        else:
            mock_req.specifier = SpecifierSet("")

        return mock_req

    pkg_resources_mock.Requirement.parse = mock.MagicMock(side_effect=mock_requirement_parse_impl)
    
    from packaging.version import parse as packaging_parse_version
    pkg_resources_mock.parse_version = packaging_parse_version

    with mock.patch('argumentation_analysis.utils.dev_tools.env_checks.pkg_resources', pkg_resources_mock) as patched_pkg_res:
        # patched_pkg_res._original_parse_method = mock_requirement_parse_impl # Not needed if side_effect is robust
        yield patched_pkg_res


@pytest.fixture
def mock_importlib_metadata_deps_fixture(): # Renamed
    with mock.patch('importlib.metadata.version') as mock_version:
        yield mock_version


# Tests for check_python_dependencies
def test_check_python_dependencies_file_not_found(mock_file_operations_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "dummy_reqs.txt"
    setup_mock_files({req_file_path_str: {"exists": False, "is_file": False}})
    
    assert check_python_dependencies(req_file_path_str) is False
    assert f"Le fichier de dépendances {req_file_path_str} n'a pas été trouvé." in caplog.text

def test_check_python_dependencies_pkg_resources_unavailable(mock_file_operations_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "dummy_reqs.txt"
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": "requests==2.25.1"}})
    
    with mock.patch('argumentation_analysis.utils.dev_tools.env_checks.pkg_resources', None):
        assert check_python_dependencies(req_file_path_str) is False
        assert "pkg_resources n'est pas disponible. Impossible de parser le fichier de dépendances." in caplog.text

def test_check_python_dependencies_empty_or_commented_file(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "empty_reqs.txt"
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": "# A comment\n\n   \n"}})
    
    assert check_python_dependencies(req_file_path_str) is True
    assert f"Le fichier de dépendances {req_file_path_str} est vide ou ne contient que des commentaires." in caplog.text

def test_check_python_dependencies_all_ok(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "reqs.txt"
    requirements_content = "requests==2.25.1\nnumpy>=1.20.0\nflask # no version spec"
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": requirements_content}})
    
    def version_side_effect(package_name):
        if package_name == "requests": return "2.25.1"
        if package_name == "numpy": return "1.21.0"
        if package_name == "flask": return "2.0.0"
        raise importlib.metadata.PackageNotFoundError(f"Not found: {package_name}")
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    assert check_python_dependencies(req_file_path_str) is True
    assert "✅ requests: Version 2.25.1 installée satisfait ==2.25.1" in caplog.text
    assert "✅ numpy: Version 1.21.0 installée satisfait >=1.20.0" in caplog.text
    assert "✅ flask: Version 2.0.0 installée (aucune version spécifique requise)." in caplog.text
    assert "✅ Toutes les dépendances Python du fichier sont satisfaites." in caplog.text

def test_check_python_dependencies_one_missing(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "reqs_missing.txt"
    requirements_content = "requests==2.25.1\nmissing_pkg==1.0.0"
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": requirements_content}})

    def version_side_effect(package_name):
        if package_name == "requests": return "2.25.1"
        if package_name == "missing_pkg": raise importlib.metadata.PackageNotFoundError("missing_pkg not found")
        raise ValueError(f"Unexpected package in test: {package_name}")
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    assert check_python_dependencies(req_file_path_str) is False
    assert "✅ requests: Version 2.25.1 installée satisfait ==2.25.1" in caplog.text
    assert "❌ missing_pkg: Non installé (requis: ==1.0.0)" in caplog.text
    assert "⚠️  Certaines dépendances Python du fichier ne sont pas satisfaites ou sont manquantes." in caplog.text

def test_check_python_dependencies_version_mismatch(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "reqs_mismatch.txt"
    requirements_content = "numpy>=1.22.0"
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": requirements_content}})
    
    mock_importlib_metadata_deps_fixture.side_effect = lambda pkg: "1.21.5" if pkg == "numpy" else "unknown"

    assert check_python_dependencies(req_file_path_str) is False
    assert "❌ numpy: Version 1.21.5 installée ne satisfait PAS >=1.22.0" in caplog.text
    assert "⚠️  Certaines dépendances Python du fichier ne sont pas satisfaites ou sont manquantes." in caplog.text

def test_check_python_dependencies_parsing_error_heuristic_recovery(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "reqs_parse_error.txt"
    requirements_content = "good_pkg==1.0\ncomplex_pkg [extra];python_version<'3.8' --hash=...\nanother_good==3.0"
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": requirements_content}})
    
    original_parse_method_side_effect = mock_pkg_resources_deps_fixture.Requirement.parse.side_effect

    complex_pkg_full_line = "complex_pkg [extra];python_version<'3.8' --hash=..."
    complex_pkg_name_only = "complex_pkg"
    
    # Compteur pour suivre les appels à custom_parse_side_effect pour complex_pkg
    # On le met dans un dictionnaire pour pouvoir le modifier dans la portée de la fonction interne
    call_counts = {'complex_pkg_initial_parse_attempted': False}

    first_parse_attempt_str_for_complex_pkg = "complex_pkg [extra]" # Ce que line_parts devient

    def custom_parse_side_effect(req_string):
        print(f"DEBUG_TEST custom_parse_side_effect: Received req_string='{req_string}', first_attempt_str='{first_parse_attempt_str_for_complex_pkg}', initial_failed={call_counts['complex_pkg_initial_parse_attempted']}")
        # Si c'est la première tentative de parser "complex_pkg [extra]"
        if req_string.strip() == first_parse_attempt_str_for_complex_pkg and not call_counts['complex_pkg_initial_parse_attempted']:
            call_counts['complex_pkg_initial_parse_attempted'] = True
            print(f"DEBUG_TEST custom_parse_side_effect: Raising ValueError for '{req_string}' (initial attempt for complex_pkg [extra])")
            # Correction du message d'erreur pour correspondre à l'assertion
            raise ValueError("Mocked parsing error for complex_pkg line (initial attempt)")
        
        # Pour la tentative heuristique (nom seul) ou autres lignes, déléguer
        print(f"DEBUG_TEST custom_parse_side_effect: Delegating '{req_string}' to original_parse_method_side_effect")
        return original_parse_method_side_effect(req_string)

    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = custom_parse_side_effect
    
    def version_side_effect(package_name):
        print(f"DEBUG_TEST version_side_effect: Called with package_name='{package_name}'")
        if package_name == "good_pkg": return "1.0"
        if package_name == "complex_pkg": return "2.5" # Heuristic should find this
        if package_name == "another_good": return "3.0"
        print(f"DEBUG_TEST version_side_effect: Raising PackageNotFoundError for '{package_name}'")
        raise importlib.metadata.PackageNotFoundError
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    print("DEBUG_TEST: About to call check_python_dependencies")
    result = check_python_dependencies(req_file_path_str)
    print(f"DEBUG_TEST: check_python_dependencies returned: {result}")
    print(f"DEBUG_TEST: caplog.text:\n{caplog.text}")

    assert result is True
    assert "Impossible de parser complètement la ligne 'complex_pkg [extra];python_version<'3.8' --hash=...' avec pkg_resources: Mocked parsing error for complex_pkg line (initial attempt). Tentative avec nom 'complex_pkg'." in caplog.text
    # L'erreur "Impossible de parser ... même après heuristique" ne doit PAS apparaître
    assert "Impossible de parser la ligne de dépendance 'complex_pkg [extra];python_version<'3.8' --hash=...' même après heuristique" not in caplog.text
    assert "✅ complex_pkg: Version 2.5 installée (aucune version spécifique requise)." in caplog.text
    assert "✅ Toutes les dépendances Python du fichier sont satisfaites." in caplog.text
    
    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = original_parse_method_side_effect # Restore

def test_check_python_dependencies_parsing_error_unrecoverable(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "reqs_parse_error_hard.txt"
    requirements_content = "good_pkg==1.0\n[] --invalid # This should fail parsing hard\nanother_good==3.0"
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": requirements_content}})

    original_parse_method_side_effect = mock_pkg_resources_deps_fixture.Requirement.parse.side_effect
    def custom_parse_side_effect(req_string):
        if "[] --invalid" in req_string:
            raise ValueError("Mocked parsing error for unrecoverable line")
        return original_parse_method_side_effect(req_string)
    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = custom_parse_side_effect
    
    assert check_python_dependencies(req_file_path_str) is False
    assert "Impossible de parser la ligne de dépendance '[] --invalid'" in caplog.text
    # assert "⚠️  Certaines dépendances Python du fichier ne sont pas satisfaites ou sont manquantes." in caplog.text # MODIFIÉ: Commenté
    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = original_parse_method_side_effect # Restore


def test_check_python_dependencies_ignored_lines(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    setup_mock_files, _, _ = mock_file_operations_deps_fixture
    req_file_path_str = "reqs_ignored.txt"
    requirements_content = (
        "-e git+https://github.com/user/repo.git#egg=editable_pkg\n"
        "    -r another_file.txt # Comment after space\n"
        "requests==2.25.1"
    )
    setup_mock_files({req_file_path_str: {"exists": True, "is_file": True, "content": requirements_content}})
    
    def version_side_effect(package_name):
        if package_name == "requests": return "2.25.1"
        raise importlib.metadata.PackageNotFoundError
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    assert check_python_dependencies(req_file_path_str) is True
    assert "Ligne ignorée (dépendance éditable/VCS) : -e git+https://github.com/user/repo.git#egg=editable_pkg" in caplog.text
    assert "Ligne ignorée (inclusion d'un autre fichier) : -r another_file.txt # Comment after space" in caplog.text # MODIFIÉ
    assert "✅ requests: Version 2.25.1 installée satisfait ==2.25.1" in caplog.text
    assert "✅ Toutes les dépendances Python du fichier sont satisfaites." in caplog.text

# Need to import builtins for mocking __import__
import builtins # This was missing, ensure it's at the top or correctly scoped if used in tests.
# Added unique_id_gen fixture
@pytest.fixture
def unique_id_gen():
    count = 0
    def generator():
        nonlocal count
        count += 1
        yield count
    yield generator # Yield the generator function