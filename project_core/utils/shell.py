import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union

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
    timeout: Optional[int] = 300
) -> subprocess.CompletedProcess:
    """
    Runs a command synchronously and returns its result.
    This is a wrapper around subprocess.run with unified logging and error handling.
    """
    command_str = ' '.join(command)
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
            shell=False  # Always false for security
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
        raise ShellCommandError(f"Command timed out: {command_str}", -1, e.stdout, e.stderr) from e
    except Exception as e:
        logger.error(f"An unexpected error occurred while running command '{command_str}': {e}")
        raise ShellCommandError(f"An unexpected error occurred: {e}", -1, "", str(e)) from e

async def run_async(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict] = None,
    check_errors: bool = True
) -> asyncio.subprocess.Process:
    """
    Runs a command asynchronously and returns the process object.
    This is a wrapper around asyncio.create_subprocess_exec.
    """
    command_str = ' '.join(command)
    logger.info(f"Running asynchronous command: {command_str} in {cwd or '.'}")

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # The caller will be responsible for await process.wait() and checking the return code
    # This asynchronous version focuses on launching the process.
    # A more complete implementation might include handling the stream reading and termination.
    logger.info(f"Asynchronous process started with PID {process.pid}: {command_str}")
    return process

async def _get_env_python_executable_async(env_name: str) -> str:
    """
    Asynchronously identifies the path to the Python executable for a given conda/venv environment.
    """
    # For now, this is a simple synchronous check wrapped in an async function.
    # In a more complex scenario, this could involve running a command asynchronously.
    return _get_env_python_executable(env_name)

async def run_in_activated_env_async(
    command: List[str],
    env_name: str = "default",
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict] = None
) -> asyncio.subprocess.Process:
    """
    Asynchronously runs a command in an activated environment.
    """
    logger.info(f"Attempting to run async command in activated env '{env_name}': {' '.join(command)}")
    try:
        python_executable = await _get_env_python_executable_async(env_name)
        full_command = [python_executable] + command
        
        return await run_async(
            command=full_command,
            cwd=cwd,
            env=env
        )
    except FileNotFoundError as e:
        logger.error(f"Could not run in activated environment. Reason: {e}")
        raise ShellCommandError(f"Failed to find environment '{env_name}'.", -1, "", str(e)) from e

import json
import os

def _get_env_python_executable(env_name: str) -> str:
    """
    Identifies the path to the Python executable for a given conda environment.
    """
    # HOTFIX: The project consistently uses a single conda environment.
    # We ignore the passed name to prevent issues from call sites
    # that might use outdated or incorrect environment names like 'projet-is' or 'default'.
    correct_env_name = "projet-is-roo-new"
    
    logger.info(f"Locating Python executable for conda env: '{correct_env_name}' (requested env: '{env_name}' was ignored)")
    try:
        # Use `conda info --json` which is faster than `conda env list`
        result = subprocess.run(
            ["conda", "info", "--json"],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            timeout=10
        )
        info_data = json.loads(result.stdout)
        
        # The target env path should be among the 'envs' list
        env_dirs = info_data.get("envs", [])
        env_path = None

        for d in env_dirs:
            # Check if the directory name matches the conda env name
            if Path(d).name == correct_env_name:
                env_path = Path(d)
                break
        
        if not env_path:
            # Fallback: check if the name is contained in the path, for unusual setups
            for d in env_dirs:
                if correct_env_name in d:
                    env_path = Path(d)
                    break
        
        if not env_path:
            raise FileNotFoundError(f"Conda environment path for '{correct_env_name}' not found in `conda info` output.")

        # Determine the executable path based on the OS
        if sys.platform == "win32":
            python_executable = env_path / "python.exe"
        else:
            python_executable = env_path / "bin" / "python"

        if not python_executable.exists():
            raise FileNotFoundError(f"Python executable not found at the expected path: {python_executable}")
        
        logger.info(f"Found Python executable for '{correct_env_name}': {python_executable}")
        return str(python_executable)

    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        logger.error(f"Failed to find Python executable for conda env '{correct_env_name}': {e}")
        # As a last resort, check the legacy '.venv' path for compatibility.
        project_root = Path(__file__).parent.parent.parent
        venv_path = project_root / ".venv"
        if sys.platform == "win32":
            legacy_executable = venv_path / "Scripts" / "python.exe"
        else:
            legacy_executable = venv_path / "bin" / "python"
        
        if legacy_executable.exists():
            logger.warning(f"Falling back to legacy .venv path: {legacy_executable}")
            return str(legacy_executable)
        
        raise ShellCommandError(f"Could not find Python executable for conda environment '{correct_env_name}'.", -1, "", str(e)) from e

def run_in_activated_env(
    command: List[str],
    env_name: str = "default",  # Keep a placeholder name
    cwd: Optional[Union[str, Path]] = None,
    check_errors: bool = True,
    timeout: Optional[int] = 600
) -> subprocess.CompletedProcess:
    """
    Abstracts away environment activation by directly using the environment's Python executable.
    """
    logger.info(f"Attempting to run command in activated environment '{env_name}': {' '.join(command)}")
    try:
        python_executable = _get_env_python_executable(env_name)
        full_command = [python_executable] + command
        
        return run_sync(
            command=full_command,
            cwd=cwd,
            check_errors=check_errors,
            timeout=timeout
        )
    except FileNotFoundError as e:
        logger.error(f"Could not run in activated environment. Reason: {e}")
        raise ShellCommandError(f"Failed to find environment '{env_name}'.", -1, "", str(e)) from e
