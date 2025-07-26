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
    Returns the path of the Python executable running the current script.
    This is the most reliable way to ensure that subprocesses use the same environment.
    """
    logger.info(f"Using current Python executable: {sys.executable} (requested env: '{env_name}')")
    return sys.executable

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
