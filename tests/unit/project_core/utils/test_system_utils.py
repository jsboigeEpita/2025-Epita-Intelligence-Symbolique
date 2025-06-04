# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires système de project_core.
"""
import pytest
from pathlib import Path
import subprocess
from unittest.mock import patch, MagicMock

from project_core.utils.system_utils import run_shell_command

@pytest.fixture
def mock_subprocess_run():
    """Fixture pour mocker subprocess.run."""
    with patch('subprocess.run') as mock_run:
        yield mock_run

def test_run_shell_command_success(mock_subprocess_run):
    """Teste l'exécution réussie d'une commande."""
    command = "ls -l"
    expected_stdout = "total 0\n-rw-r--r-- 1 user group 0 Jan 1 00:00 file.txt"
    expected_stderr = ""
    expected_return_code = 0

    mock_process = MagicMock()
    mock_process.stdout = expected_stdout
    mock_process.stderr = expected_stderr
    mock_process.returncode = expected_return_code
    mock_subprocess_run.return_value = mock_process

    ret_code, out, err = run_shell_command(command)

    assert ret_code == expected_return_code
    assert out == expected_stdout.strip() # .strip() est appliqué dans la fonction
    assert err == expected_stderr.strip()
    mock_subprocess_run.assert_called_once_with(
        ["ls", "-l"], # shlex.split(command)
        cwd=None,
        capture_output=True,
        text=True,
        timeout=60, # Default timeout
        check=False
    )

def test_run_shell_command_with_error_output(mock_subprocess_run):
    """Teste une commande qui réussit mais produit une sortie d'erreur."""
    command = "my_script --verbose"
    expected_stdout = "Operation successful."
    expected_stderr = "WARN: Deprecated feature used."
    expected_return_code = 0

    mock_process = MagicMock()
    mock_process.stdout = expected_stdout
    mock_process.stderr = expected_stderr
    mock_process.returncode = expected_return_code
    mock_subprocess_run.return_value = mock_process

    ret_code, out, err = run_shell_command(command)

    assert ret_code == expected_return_code
    assert out == expected_stdout.strip()
    assert err == expected_stderr.strip()

def test_run_shell_command_failure_return_code(mock_subprocess_run):
    """Teste une commande qui échoue avec un code de retour non nul."""
    command = "failing_command"
    expected_stdout = ""
    expected_stderr = "Error: Something went wrong."
    expected_return_code = 1

    mock_process = MagicMock()
    mock_process.stdout = expected_stdout
    mock_process.stderr = expected_stderr
    mock_process.returncode = expected_return_code
    mock_subprocess_run.return_value = mock_process

    ret_code, out, err = run_shell_command(command)

    assert ret_code == expected_return_code
    assert out == expected_stdout
    assert err == expected_stderr.strip()

def test_run_shell_command_timeout(mock_subprocess_run, caplog):
    """Teste la gestion d'un timeout de commande."""
    command = "sleep 10"
    timeout_seconds = 2

    # Simuler TimeoutExpired
    # L'exception TimeoutExpired a des attributs stdout et stderr (en bytes)
    timeout_exception = subprocess.TimeoutExpired(cmd=command, timeout=timeout_seconds)
    timeout_exception.stdout = b"Partial output before timeout"
    timeout_exception.stderr = b"Partial error before timeout"
    mock_subprocess_run.side_effect = timeout_exception

    ret_code, out, err = run_shell_command(command, timeout_seconds=timeout_seconds)

    assert ret_code == -9 # Code spécifique pour timeout
    assert out == "Partial output before timeout" # Décodé et strippé
    assert err == "Partial error before timeout"
    assert f"La commande '{command}' a expiré après {timeout_seconds} secondes." in caplog.text

def test_run_shell_command_file_not_found(mock_subprocess_run, caplog):
    """Teste la gestion d'une commande non trouvée (FileNotFoundError)."""
    command = "command_that_does_not_exist"
    
    # Simuler FileNotFoundError
    mock_subprocess_run.side_effect = FileNotFoundError(f"[Errno 2] No such file or directory: '{command.split()[0]}'")

    ret_code, out, err = run_shell_command(command)

    assert ret_code == -10 # Code spécifique pour FileNotFoundError
    assert out == ""
    assert f"Commande non trouvée: {command.split()[0]}" in err
    assert f"Erreur : La commande ou l'exécutable '{command.split()[0]}' n'a pas été trouvé." in caplog.text

def test_run_shell_command_unexpected_exception(mock_subprocess_run, caplog):
    """Teste la gestion d'une exception générique inattendue."""
    command = "command_with_other_problem"
    
    # Simuler une exception générique
    # L'exception peut avoir ou non stdout/stderr.
    generic_exception = Exception("A very unexpected error occurred.")
    # setattr(generic_exception, 'stdout', b"stdout from generic error") # Optionnel
    # setattr(generic_exception, 'stderr', b"stderr from generic error") # Optionnel
    mock_subprocess_run.side_effect = generic_exception

    ret_code, out, err = run_shell_command(command)

    assert ret_code == -11 # Code spécifique pour autre exception
    # out et err peuvent être vides ou contenir des infos de l'exception
    # Ici, on s'attend à ce que err contienne la description de l'exception.
    assert "A very unexpected error occurred." in err 
    assert f"Une erreur inattendue est survenue lors de l'exécution de '{command}'" in caplog.text

def test_run_shell_command_with_work_dir(mock_subprocess_run, tmp_path):
    """Teste l'exécution d'une commande avec un répertoire de travail spécifié."""
    command = "pwd"
    work_dir = tmp_path / "my_work_dir"
    work_dir.mkdir() # Le répertoire doit exister pour subprocess.run

    expected_stdout = str(work_dir.resolve())
    mock_process = MagicMock()
    mock_process.stdout = expected_stdout
    mock_process.stderr = ""
    mock_process.returncode = 0
    mock_subprocess_run.return_value = mock_process

    ret_code, out, err = run_shell_command(command, work_dir=work_dir)

    assert ret_code == 0
    assert out == expected_stdout.strip()
    mock_subprocess_run.assert_called_once_with(
        ["pwd"], # shlex.split(command)
        cwd=work_dir, # Vérifie que work_dir est passé
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )

def test_run_shell_command_empty_command_string(caplog):
    """Teste le comportement avec une chaîne de commande vide."""
    # shlex.split('') -> []
    # subprocess.run([]) lèvera probablement une exception (FileNotFoundError ou autre)
    # car il n'y a pas de commande à exécuter.
    ret_code, out, err = run_shell_command("")
    
    assert ret_code == -11 # OSError: [WinError 87] Paramètre incorrect est capturée par le except Exception générique
    assert "Paramètre incorrect" in err # Vérifie une partie du message de OSError
    # Le log devrait indiquer une erreur générique car OSError est attrapée par le bloc Exception
    assert "Une erreur inattendue est survenue lors de l'exécution de '': OSError - [WinError 87] Paramètre incorrect" in caplog.text
    # Les commentaires et assertions précédents supposaient un FileNotFoundError ou IndexError,
    # mais c'est une OSError sur Windows pour une commande vide passée à subprocess.run,
    # qui est ensuite attrapée par le bloc `except Exception`.