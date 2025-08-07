import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union, Dict
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ShellCommandError(Exception):
    """Custom exception for shell command errors."""
    def __init__(self, message, returncode, stdout, stderr):
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return f"{self.args[0]}\nReturn Code: {self.returncode}\nSTDOUT: {self.stdout}\nSTDERR: {self.stderr}"

def run_sync(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    capture_output: bool = True,
    check_errors: bool = True,
    timeout: Optional[int] = 300,
    env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess:
    """
    Runs a command synchronously and returns its result.
    This is a wrapper around subprocess.run with unified logging and error handling.
    """
    command_str = ' '.join(str(c) for c in command)
    logger.info(f"Running synchronous command: {command_str} in {cwd or '.'}")

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            encoding='utf-8',
            check=False,  # We check manually to raise our custom exception
            timeout=timeout,
            shell=False,  # Always false for security
            env=env
        )

        if check_errors and result.returncode != 0:
            raise ShellCommandError(
                f"Command failed with return code {result.returncode}",
                result.returncode,
                result.stdout,
                result.stderr
            )
        
        logger.info(f"Command executed successfully: {command_str}")
        return result

    except FileNotFoundError as e:
        logger.error(f"Command not found: {command[0]}. Original error: {e}")
        raise ShellCommandError(f"Command not found: {command[0]}", -1, "", str(e)) from e
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout}s: {command_str}")
        raise ShellCommandError(f"Command timed out: {command_str}", -1, e.stdout or "", e.stderr or "") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred while running command '{command_str}': {e}")
        raise ShellCommandError(f"An unexpected error occurred: {e}", -1, "", str(e)) from e

async def run_async(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
) -> asyncio.subprocess.Process:
    """
    Runs a command asynchronously and returns the process object.
    This is a wrapper around asyncio.create_subprocess_exec.
    """
    command_str = ' '.join(command)
    logger.info(f"Running asynchronous command: {command_str} in {cwd or '.'}")

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    logger.info(f"Asynchronous process started with PID {process.pid}: {command_str}")
    return process

# --- Environment Activation Logic ---

def _find_conda_executable():
    """Finds the path to the conda executable."""
    # Common locations for conda
    for path in [
        os.path.join(sys.prefix, 'condabin', 'conda.bat'),  # Conda base env
        os.path.join(sys.prefix, 'Scripts', 'conda.exe'),   # Other envs
        os.path.expanduser('~/anaconda3/Scripts/conda.exe'),
        os.path.expanduser('~/miniconda3/Scripts/conda.exe'),
    ]:
        if os.path.exists(path):
            return path
    # Check PATH
    try:
        result = subprocess.run(['where', 'conda'], capture_output=True, text=True, check=True, shell=True)
        return result.stdout.strip().split('\n')[0]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def _get_env_python_executable(env_name: str) -> str:
    """
    Identifies the path to the Python executable for a given conda or venv environment.
    If 'default' or current env, returns sys.executable.
    """
    if env_name == "default" or env_name == os.path.basename(sys.prefix):
        logger.info(f"Using current Python executable for env '{env_name}': {sys.executable}")
        return sys.executable

    # 1. Check for Conda environment
    conda_exe = _find_conda_executable()
    if conda_exe:
        try:
            cmd = [conda_exe, 'env', 'list', '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
            envs = json.loads(result.stdout)['envs']
            for env_path in envs:
                if os.path.basename(env_path) == env_name:
                    py_exe = os.path.join(env_path, 'python.exe')
                    if os.path.exists(py_exe):
                        logger.info(f"Found Python executable for conda env '{env_name}': {py_exe}")
                        return py_exe
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not list or parse conda environments: {e}. Falling back.")

    # 2. Check for venv (assuming it's in a standard location relative to project root)
    # This part can be made more robust if there's a convention for venv locations
    project_root = Path(__file__).resolve().parents[2] # Adjust depth as needed
    venv_path = project_root / 'venvs' / env_name / 'Scripts' / 'python.exe'
    if venv_path.exists():
        logger.info(f"Found Python executable for venv '{env_name}': {venv_path}")
        return str(venv_path)

    raise FileNotFoundError(f"Could not find Python executable for environment '{env_name}'.")


async def _get_env_python_executable_async(env_name: str) -> str:
    """Asynchronously identifies the path to the Python executable."""
    # Wrapping the synchronous version for now.
    # A fully async version would use asyncio.create_subprocess_exec.
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_env_python_executable, env_name)

# --- Unified Functions ---

def run_in_activated_env(
    command: List[str],
    env_name: str,
    cwd: Optional[Union[str, Path]] = None,
    check_errors: bool = True,
    timeout: Optional[int] = 600,
    env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess:
    """
    Abstracts away environment activation by directly using the environment's Python executable.
    """
    logger.info(f"Attempting to run sync command in activated env '{env_name}': {' '.join(command)}")
    try:
        python_executable = _get_env_python_executable(env_name)
        # For commands like 'pip', 'pytest', etc., use '-m' for robustness
        if command[0] in ['pip', 'pytest', 'python']:
             full_command = [python_executable, '-m'] + command[1:] if len(command) > 1 else [python_executable]
             if command[0] not in ['python']:
                 full_command.insert(1, command[0])

        else:
             full_command = [python_executable] + command
        
        return run_sync(
            command=full_command,
            cwd=cwd,
            check_errors=check_errors,
            timeout=timeout,
            env=env
        )
    except FileNotFoundError as e:
        logger.error(f"Could not run in activated environment. Reason: {e}")
        raise ShellCommandError(f"Failed to find environment '{env_name}'.", -1, "", str(e)) from e

async def run_in_activated_env_async(
    command: List[str],
    env_name: str,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None
) -> asyncio.subprocess.Process:
    """
    Asynchronously runs a command in an activated environment.
    """
    logger.info(f"Attempting to run async command in activated env '{env_name}': {' '.join(command)}")
    try:
        python_executable = await _get_env_python_executable_async(env_name)
        if command[0] in ['pip', 'pytest', 'python']:
             full_command = [python_executable, '-m'] + command[1:] if len(command) > 1 else [python_executable]
             if command[0] not in ['python']:
                 full_command.insert(1, command[0])
        else:
            full_command = [python_executable] + command
        
        return await run_async(
            command=full_command,
            cwd=cwd,
            env=env
        )
    except FileNotFoundError as e:
        logger.error(f"Could not run in activated environment. Reason: {e}")
        raise ShellCommandError(f"Failed to find environment '{env_name}'.", -1, "", str(e)) from e
