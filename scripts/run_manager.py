import sys
from project_core.managers.environment_manager import EnvironmentManager

if __name__ == "__main__":
    manager = EnvironmentManager()
    exit_code = manager.run_command_in_conda_env(sys.argv[1:])
    sys.exit(exit_code)