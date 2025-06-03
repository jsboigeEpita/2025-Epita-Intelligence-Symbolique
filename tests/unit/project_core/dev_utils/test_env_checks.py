import pytest
import subprocess
import importlib.metadata
import os
from pathlib import Path
from unittest import mock

# Import the functions to be tested
from argumentation_analysis.utils.dev_tools.env_checks import (
    check_java_environment,
    check_jpype_config,
    check_python_dependencies,
    _run_command  # If we want to test it directly or mock its usage precisely
)

# Mocks for check_java_environment
@pytest.fixture
def mock_os_environ_java():
    with mock.patch.dict(os.environ, {}, clear=True) as mock_env:
        yield mock_env

@pytest.fixture
def mock_path_java():
    with mock.patch('project_core.dev_utils.env_checks.Path') as mock_path_constructor:
        mock_path_instance = mock.Mock(spec=Path)
        mock_path_constructor.return_value = mock_path_instance
        
        # Default behaviors for Path methods
        mock_path_instance.is_dir.return_value = False
        mock_path_instance.exists.return_value = False
        mock_path_instance.is_file.return_value = False
        
        # Allow configuring specific sub-paths like JAVA_HOME/bin/java
        def configure_java_exe_path(is_dir, java_exe_exists, java_exe_is_file):
            bin_path_mock = mock.Mock(spec=Path)
            java_exe_mock = mock.Mock(spec=Path)
            
            mock_path_instance.is_dir.return_value = is_dir
            mock_path_instance.__truediv__.return_value = bin_path_mock # for path / "bin"
            bin_path_mock.__truediv__.return_value = java_exe_mock    # for bin_path / "java"
            
            java_exe_mock.exists.return_value = java_exe_exists
            java_exe_mock.is_file.return_value = java_exe_is_file
            return mock_path_instance, java_exe_mock

        mock_path_instance.configure_java_exe_path = configure_java_exe_path
        yield mock_path_instance

@pytest.fixture
def mock_run_command_java():
    # This mocks the _run_command function within the env_checks module
    with mock.patch('project_core.dev_utils.env_checks._run_command') as mock_run:
        yield mock_run

# Tests for check_java_environment
def test_check_java_environment_all_ok(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir=True, java_exe_exists=True, java_exe_is_file=True)
    mock_run_command_java.return_value = (0, "", "java version \"11.0.1\" 2021-04-20") # stdout, stderr

    assert check_java_environment() is True
    assert "JAVA_HOME est défini : /opt/java" in caplog.text
    assert "JAVA_HOME pointe vers un répertoire Java valide" in caplog.text
    assert "Commande 'java -version' exécutée avec succès. Version détectée : java version \"11.0.1\"" in caplog.text
    assert "L'environnement Java est jugé correctement configuré" in caplog.text

def test_check_java_environment_no_java_home_version_ok(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    # JAVA_HOME is not set (default from mock_os_environ_java)
    mock_run_command_java.return_value = (0, "", "openjdk version \"1.8.0_292\"")
    
    assert check_java_environment() is False # Fails because JAVA_HOME is critical for "correctly configured"
    assert "JAVA_HOME n'est pas défini" in caplog.text
    assert "Commande 'java -version' exécutée avec succès." in caplog.text
    assert "Bien que 'java -version' fonctionne, JAVA_HOME n'est pas défini ou est invalide." in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_home_invalid_dir(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/invalid/java_home"
    mock_path_java.is_dir.return_value = False # JAVA_HOME path is not a dir
    mock_run_command_java.return_value = (0, "", "openjdk version \"1.8.0_292\"")

    assert check_java_environment() is False
    assert "JAVA_HOME (/invalid/java_home) n'est pas un répertoire valide." in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_home_no_java_exe(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java_no_exe"
    # Path for JAVA_HOME itself is a dir, but bin/java doesn't exist or isn't a file
    mock_path_java.configure_java_exe_path(is_dir=True, java_exe_exists=False, java_exe_is_file=False)
    mock_run_command_java.return_value = (0, "", "openjdk version \"1.8.0_292\"")

    assert check_java_environment() is False
    assert "JAVA_HOME (/opt/java_no_exe) ne semble pas contenir une installation Java valide" in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_version_fails_filenotfound(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir=True, java_exe_exists=True, java_exe_is_file=True)
    mock_run_command_java.return_value = (-1, "", "FileNotFoundError: java") # Simulating _run_command's FileNotFoundError case

    assert check_java_environment() is False
    assert "Échec de l'exécution de 'java -version'." in caplog.text # This comes from _run_command via logger
    assert "Java n'est pas trouvé dans le PATH ou n'est pas exécutable." in caplog.text # This is from check_java_environment
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_version_fails_returncode(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir=True, java_exe_exists=True, java_exe_is_file=True)
    mock_run_command_java.return_value = (1, "stdout error", "stderr error")

    assert check_java_environment() is False
    assert "Échec de l'exécution de 'java -version'. Code de retour : 1" in caplog.text
    assert "Stderr: stderr error" in caplog.text
    assert "L'environnement Java n'est pas considéré comme correctement configuré." in caplog.text

def test_check_java_environment_java_version_ok_no_output(mock_os_environ_java, mock_path_java, mock_run_command_java, caplog):
    mock_os_environ_java["JAVA_HOME"] = "/opt/java"
    mock_path_java.configure_java_exe_path(is_dir=True, java_exe_exists=True, java_exe_is_file=True)
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
    import builtins
    original_import = builtins.__import__
    def import_side_effect(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'jpype':
            raise ImportError("Simulated JPype import error")
        return original_import(name, globals, locals, fromlist, level)

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
def mock_file_operations_deps_fixture(): # Renamed
    mock_path_instance = mock.Mock(spec=Path)
    mock_path_instance.is_file.return_value = True
    mock_open_func = mock.mock_open()

    with mock.patch('project_core.dev_utils.env_checks.Path', return_value=mock_path_instance) as mock_path_constructor, \
         mock.patch('builtins.open', mock_open_func) as mock_open_builtin: # Renamed mock_open to mock_open_builtin
        yield {
            "path_constructor": mock_path_constructor,
            "path_instance": mock_path_instance,
            "open": mock_open_builtin, # Use the renamed mock
            "mock_open_func": mock_open_func
        }

@pytest.fixture
def mock_pkg_resources_deps_fixture(): # Renamed
    pkg_resources_mock = mock.MagicMock(name="pkg_resources_module")
    
    # Store the original parse method to call it for non-custom cases
    # This requires pkg_resources to be actually available in the test environment
    # or a more sophisticated mock for Requirement.parse.
    # For simplicity, we'll make a flexible mock here.
    def mock_requirement_parse_impl(req_string):
        mock_req = mock.Mock()
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

    with mock.patch('project_core.dev_utils.env_checks.pkg_resources', pkg_resources_mock) as patched_pkg_res:
        patched_pkg_res._original_parse_method = mock_requirement_parse_impl
        yield patched_pkg_res


@pytest.fixture
def mock_importlib_metadata_deps_fixture(): # Renamed
    with mock.patch('importlib.metadata.version') as mock_version:
        yield mock_version


# Tests for check_python_dependencies
def test_check_python_dependencies_file_not_found(mock_file_operations_deps_fixture, caplog):
    mock_file_operations_deps_fixture["path_instance"].is_file.return_value = False
    req_file_path = Path("dummy_reqs.txt")
    
    assert check_python_dependencies(req_file_path) is False
    assert f"Le fichier de dépendances {str(req_file_path)} n'a pas été trouvé." in caplog.text

def test_check_python_dependencies_pkg_resources_unavailable(mock_file_operations_deps_fixture, caplog):
    req_file_path = Path("dummy_reqs.txt")
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = "requests==2.25.1"
    
    with mock.patch('project_core.dev_utils.env_checks.pkg_resources', None):
        assert check_python_dependencies(req_file_path) is False
        assert "pkg_resources n'est pas disponible. Impossible de parser le fichier de dépendances." in caplog.text

def test_check_python_dependencies_empty_or_commented_file(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, caplog):
    req_file_path = Path("empty_reqs.txt")
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = "# A comment\n\n   \n"
    
    assert check_python_dependencies(req_file_path) is True
    assert f"Le fichier de dépendances {str(req_file_path)} est vide ou ne contient que des commentaires." in caplog.text

def test_check_python_dependencies_all_ok(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    req_file_path = Path("reqs.txt")
    requirements_content = "requests==2.25.1\nnumpy>=1.20.0\nflask # no version spec"
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = requirements_content
    
    def version_side_effect(package_name):
        if package_name == "requests": return "2.25.1"
        if package_name == "numpy": return "1.21.0"
        if package_name == "flask": return "2.0.0"
        raise importlib.metadata.PackageNotFoundError(f"Not found: {package_name}")
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    assert check_python_dependencies(req_file_path) is True
    assert "✅ requests: Version 2.25.1 installée satisfait ==2.25.1" in caplog.text
    assert "✅ numpy: Version 1.21.0 installée satisfait >=1.20.0" in caplog.text
    assert "✅ flask: Version 2.0.0 installée (aucune version spécifique requise)." in caplog.text
    assert "✅ Toutes les dépendances Python du fichier sont satisfaites." in caplog.text

def test_check_python_dependencies_one_missing(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    req_file_path = Path("reqs_missing.txt")
    requirements_content = "requests==2.25.1\nmissing_pkg==1.0.0"
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = requirements_content

    def version_side_effect(package_name):
        if package_name == "requests": return "2.25.1"
        if package_name == "missing_pkg": raise importlib.metadata.PackageNotFoundError("missing_pkg not found")
        raise ValueError(f"Unexpected package in test: {package_name}")
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    assert check_python_dependencies(req_file_path) is False
    assert "✅ requests: Version 2.25.1 installée satisfait ==2.25.1" in caplog.text
    assert "❌ missing_pkg: Non installé (requis: ==1.0.0)" in caplog.text
    assert "⚠️  Certaines dépendances Python du fichier ne sont pas satisfaites ou sont manquantes." in caplog.text

def test_check_python_dependencies_version_mismatch(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    req_file_path = Path("reqs_mismatch.txt")
    requirements_content = "numpy>=1.22.0"
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = requirements_content
    
    mock_importlib_metadata_deps_fixture.side_effect = lambda pkg: "1.21.5" if pkg == "numpy" else "unknown"

    assert check_python_dependencies(req_file_path) is False
    assert "❌ numpy: Version 1.21.5 installée ne satisfait PAS >=1.22.0" in caplog.text
    assert "⚠️  Certaines dépendances Python du fichier ne sont pas satisfaites ou sont manquantes." in caplog.text

def test_check_python_dependencies_parsing_error_heuristic_recovery(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    req_file_path = Path("reqs_parse_error.txt")
    requirements_content = "good_pkg==1.0\ncomplex_pkg [extra];python_version<'3.8' --hash=...\nanother_good==3.0"
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = requirements_content
    
    original_parse_method = mock_pkg_resources_deps_fixture.Requirement.parse.side_effect

    def custom_parse_side_effect(req_string):
        if "complex_pkg" in req_string: # Target the complex line for simulated failure
            # Simulate the ValueError that triggers the heuristic in the SUT
            raise ValueError("Mocked parsing error for complex_pkg line")
        # For other lines, delegate to the original mock implementation
        return original_parse_method(req_string)
    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = custom_parse_side_effect
    
    def version_side_effect(package_name):
        if package_name == "good_pkg": return "1.0"
        # The heuristic in SUT should extract "complex_pkg" as the name
        if package_name == "complex_pkg": return "2.5"
        if package_name == "another_good": return "3.0"
        raise importlib.metadata.PackageNotFoundError
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    assert check_python_dependencies(req_file_path) is True
    assert "Impossible de parser complètement la ligne 'complex_pkg [extra];python_version<'3.8' --hash=...'" in caplog.text
    assert "Tentative avec nom 'complex_pkg'" in caplog.text
    assert "✅ complex_pkg: Version 2.5 installée (aucune version spécifique requise)." in caplog.text
    assert "✅ Toutes les dépendances Python du fichier sont satisfaites." in caplog.text
    
    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = original_parse_method

def test_check_python_dependencies_parsing_error_unrecoverable(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, caplog):
    req_file_path = Path("reqs_parse_error_hard.txt")
    requirements_content = "good_pkg==1.0\n[] --invalid # This should fail parsing hard\nanother_good==3.0"
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = requirements_content

    original_parse_method = mock_pkg_resources_deps_fixture.Requirement.parse.side_effect
    def custom_parse_side_effect(req_string):
        if "[] --invalid" in req_string:
            raise ValueError("Mocked parsing error for unrecoverable line")
        return original_parse_method(req_string)
    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = custom_parse_side_effect
    
    assert check_python_dependencies(req_file_path) is False
    assert "Impossible de parser la ligne de dépendance '[] --invalid'" in caplog.text
    assert "⚠️  Certaines dépendances Python du fichier ne sont pas satisfaites ou sont manquantes." in caplog.text
    mock_pkg_resources_deps_fixture.Requirement.parse.side_effect = original_parse_method


def test_check_python_dependencies_ignored_lines(mock_file_operations_deps_fixture, mock_pkg_resources_deps_fixture, mock_importlib_metadata_deps_fixture, caplog):
    req_file_path = Path("reqs_ignored.txt")
    requirements_content = (
        "-e git+https://github.com/user/repo.git#egg=editable_pkg\n"
        "    -r another_file.txt # Comment after space\n"
        "requests==2.25.1"
    )
    mock_file_operations_deps_fixture["mock_open_func"].return_value.read.return_value = requirements_content
    
    def version_side_effect(package_name):
        if package_name == "requests": return "2.25.1"
        raise importlib.metadata.PackageNotFoundError
    mock_importlib_metadata_deps_fixture.side_effect = version_side_effect

    assert check_python_dependencies(req_file_path) is True
    assert "Ligne ignorée (dépendance éditable/VCS) : -e git+https://github.com/user/repo.git#egg=editable_pkg" in caplog.text
    assert "Ligne ignorée (inclusion d'un autre fichier) : -r another_file.txt" in caplog.text
    assert "✅ requests: Version 2.25.1 installée satisfait ==2.25.1" in caplog.text
    assert "✅ Toutes les dépendances Python du fichier sont satisfaites." in caplog.text

# Need to import builtins for mocking __import__
import builtins