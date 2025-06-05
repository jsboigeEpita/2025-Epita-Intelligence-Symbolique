# main_setup.py
import os
import sys

# Déterminer la racine du projet et l'ajouter à sys.path pour prioriser les modules locaux
# Le script est dans scripts/setup_core, donc remonter de deux niveaux
_current_script_path_for_sys_path = os.path.abspath(__file__)
_setup_core_dir_for_sys_path = os.path.dirname(_current_script_path_for_sys_path)
_scripts_dir_for_sys_path = os.path.dirname(_setup_core_dir_for_sys_path)
_project_root_for_sys_path = os.path.dirname(_scripts_dir_for_sys_path)
if _project_root_for_sys_path not in sys.path:
    sys.path.insert(0, _project_root_for_sys_path)
print(f"[DEBUG_ROO] sys.path[0] is now: {sys.path[0]}") # Log pour vérifier

import argparse
import sys
import os

import subprocess
# Placeholder pour les futurs modules
import scripts.setup_core.manage_conda_env as manage_conda_env
import scripts.setup_core.manage_portable_tools as manage_portable_tools
print(f"[DEBUG_ROO] Loaded manage_portable_tools from: {manage_portable_tools.__file__}")
import scripts.setup_core.manage_project_files as manage_project_files
import scripts.setup_core.run_pip_commands as run_pip_commands
import scripts.setup_core.env_utils as env_utils # Ajout de l'importation
 
def main():
    # Déterminer la racine du projet pour la passer aux modules de configuration
    # Le script est dans scripts/setup_core, donc remonter de deux niveaux
    current_script_path = os.path.abspath(__file__)
    setup_core_dir = os.path.dirname(current_script_path)
    scripts_dir = os.path.dirname(setup_core_dir)
    project_root = os.path.dirname(scripts_dir)

    tools_dir_default = os.path.join(project_root, ".tools")

    parser = argparse.ArgumentParser(description="Project Environment Setup Orchestrator.")
    parser.add_argument("--force-reinstall-tools", action="store_true", help="Force reinstall portable tools (JDK, Octave).")
    parser.add_argument("--force-reinstall-env", action="store_true", help="Force reinstall Conda environment.")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive mode for confirmations.")
    parser.add_argument("--skip-tools", action="store_true", help="Skip portable tools installation.")
    parser.add_argument("--skip-env", action="store_true", help="Skip Conda environment setup.")
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip cleanup of old installations.")
    parser.add_argument("--skip-pip-install", action="store_true", help="Skip pip install dependencies.")
    parser.add_argument("--run-pytest-debug", action="store_true", help="Run pytest with debug info after setup.")
    # Ajoutez d'autres arguments si pertinent après analyse de setup_project_env.ps1
 
    args = parser.parse_args()

    print("Starting project setup with the following options:")
    print(f"  Force reinstall tools: {args.force_reinstall_tools}")
    print(f"  Force reinstall env: {args.force_reinstall_env}")
    print(f"  Interactive mode: {args.interactive}")
    print(f"  Skip tools: {args.skip_tools}")
    print(f"  Skip Conda env: {args.skip_env}")
    print(f"  Skip cleanup: {args.skip_cleanup}")
    print(f"  Skip pip install: {args.skip_pip_install}")
    print(f"  Run pytest debug: {args.run_pytest_debug}")
    print("-" * 30)
 
    tool_paths = None # Initialiser tool_paths
    if not args.skip_tools:
        print("[INFO] Managing portable tools (JDK, Octave)...")
        # Définir le répertoire des outils
        tools_target_dir = tools_dir_default # Peut être rendu configurable via args plus tard
        print(f"[INFO] Portable tools will be installed/checked in: {tools_target_dir}")
        
        tool_paths = manage_portable_tools.setup_tools(
            tools_dir_base_path=tools_target_dir,
            force_reinstall=args.force_reinstall_tools,
            interactive=args.interactive
            # Les options skip_jdk, skip_octave pourraient être ajoutées ici si besoin
            # skip_jdk=args.skip_jdk, # Nécessiterait d'ajouter --skip-jdk à argparse
            # skip_octave=args.skip_octave # Nécessiterait d'ajouter --skip-octave à argparse
        )
        if tool_paths:
            print("[INFO] Paths for configured tools:")
            for env_var, path in tool_paths.items():
                print(f"  {env_var}: {path}")
        else:
            print("[INFO] No portable tools were configured or paths returned.")
            tool_paths = {} # S'assurer que c'est un dictionnaire pour l'appel suivant
    else:
        print("[INFO] Skipping portable tools installation.")

    if not args.skip_env:
        print("[INFO] Managing Conda environment...")
        try:
            conda_env_name = env_utils.get_conda_env_name_from_yaml()
            print(f"[INFO] Nom de l'environnement Conda récupéré depuis environment.yml: {conda_env_name}")
        except Exception as e:
            print(f"[ERROR] Impossible de récupérer le nom de l'environnement Conda depuis environment.yml: {e}")
            print("[INFO] Utilisation du nom par défaut 'epita_symbolic_ai' pour l'environnement Conda.")
            conda_env_name = "epita_symbolic_ai" # Fallback au cas où la lecture échoue
        
        conda_env_file = os.path.join(project_root, "environment.yml")
        
        env_setup_success = manage_conda_env.setup_environment(
            env_name=conda_env_name,
            env_file_path=conda_env_file,
            project_root=project_root,
            force_reinstall=args.force_reinstall_env,
            interactive=args.interactive
        )
        if env_setup_success:
            print(f"[SUCCESS] Conda environment '{conda_env_name}' is ready.")
        else:
            print(f"[ERROR] Failed to set up Conda environment '{conda_env_name}'.")
            # Potentiellement, sortir ou lever une exception ici si l'environnement est critique
        
        print("[INFO] Managing project files (.env, cleanup)...")
        manage_project_files.setup_project_structure(
            project_root=project_root,
            tool_paths=tool_paths, # tool_paths est initialisé à None ou rempli par setup_tools
            interactive=args.interactive,
            perform_cleanup=not args.skip_cleanup
        )
        
        if not args.skip_pip_install:
            print("[INFO] Running pip commands to install project dependencies...")
            pip_success = run_pip_commands.install_project_dependencies(
                project_root=project_root,
                conda_env_name=conda_env_name # Assurez-vous que conda_env_name est défini dans ce scope
            )
            if pip_success:
                print("[SUCCESS] Project dependencies installed successfully via pip.")
            else:
                print("[ERROR] Failed to install project dependencies via pip.")
                # Gérer l'échec si nécessaire, par exemple, sortir du script
        else:
            print("[INFO] Skipping pip install dependencies.")
    else:
        print("[INFO] Skipping Conda environment setup (and pip commands, project files setup).")

    if args.run_pytest_debug:
        if args.skip_env: # Cette vérification est pertinente ici, car on pourrait vouloir skipper l'env mais quand même tenter le debug
            print("[WARNING] --run-pytest-debug was specified, and --skip-env was also specified. Pytest will run in the currently active environment, if any, or the base environment.")
        
        print("[INFO] Attempting to run pytest with debug information...")
        try:
            # Récupérer conda_env_name si l'environnement n'a pas été skippé, sinon il n'est pas pertinent
            # ou on pourrait tenter de le deviner si nécessaire pour un `conda run`
            conda_env_name_for_debug = "epita_symbolic_ai" # Valeur par défaut ou à déterminer
            if not args.skip_env and 'conda_env_name' in locals() and conda_env_name:
                conda_env_name_for_debug = conda_env_name
            elif 'conda_env_name' in locals() and conda_env_name: # Cas où skip_env mais conda_env_name a été défini plus tôt
                 conda_env_name_for_debug = conda_env_name
            else: # Fallback si conda_env_name n'a jamais été défini (par ex. si --skip-env et lecture yaml échoue)
                try:
                    conda_env_name_for_debug = env_utils.get_conda_env_name_from_yaml()
                except Exception:
                    pass # Garder la valeur par défaut "epita_symbolic_ai"

            print(f"[INFO] Target Conda environment for debug (if applicable for activation): {conda_env_name_for_debug}")
            
            # Commande PowerShell à exécuter à l'intérieur de l'environnement Conda
            final_ps_command_block = f"""
            Write-Host '--- Debug Info Start (inside conda run) ---'
            Write-Host "CONDA_DEFAULT_ENV: $env:CONDA_DEFAULT_ENV"
            Write-Host "CONDA_PREFIX: $env:CONDA_PREFIX"
            Write-Host "PYTHONPATH: $env:PYTHONPATH"
            Write-Host "PATH (first 200 chars): $($env:PATH.Substring(0, [System.Math]::Min($env:PATH.Length, 200))) ..."
            conda env list
            Write-Host '--- Debug Info End (inside conda run) ---'
            pytest
            """
            
            # Contenu du script PowerShell temporaire
            temp_ps_script_content = f"""
            Write-Host "--- Attempting to activate {conda_env_name_for_debug} within temp script ---"
            try {{
                conda activate {conda_env_name_for_debug}
                Write-Host "CONDA_PREFIX after explicit activate: $env:CONDA_PREFIX"
                if ($env:CONDA_PREFIX) {{
                    $EnvScriptsPath = Join-Path $env:CONDA_PREFIX 'Scripts'
                    $env:PATH = $EnvScriptsPath + ';' + $env:PATH
                    Write-Host "PATH updated with $EnvScriptsPath"
                }}
            }}
            catch {{
                Write-Warning "Failed to explicitly activate {conda_env_name_for_debug} or update PATH in temp script. Error: $($_.Exception.Message)"
            }}

            Write-Host '--- Debug Info Start (inside conda run via temp script) ---'
            Write-Host "CONDA_DEFAULT_ENV: $env:CONDA_DEFAULT_ENV"
            Write-Host "CONDA_PREFIX: $env:CONDA_PREFIX"
            Write-Host "PYTHONPATH: $env:PYTHONPATH"
            Write-Host "PATH (first 200 chars): $($env:PATH.Substring(0, [System.Math]::Min($env:PATH.Length, 200))) ..."
            conda env list
            Write-Host '--- Debug Info End (inside conda run via temp script) ---'
            pytest
            """
            
            # Utiliser project_root qui est défini au début de la fonction main()
            temp_script_path = os.path.join(project_root, "temp_debug_pytest.ps1")
            
            try:
                with open(temp_script_path, "w", encoding="utf-8") as f:
                    f.write(temp_ps_script_content)
                
                conda_run_args = [
                    "conda", "run", "-n", conda_env_name_for_debug,
                    # "--no-capture-output", # On va capturer pour l'analyse
                    "powershell", "-ExecutionPolicy", "Bypass", "-File", temp_script_path
                ]
                
                print(f"[INFO] Executing conda run with temp script: {' '.join(conda_run_args)}")
                completed_process = subprocess.run(conda_run_args, shell=False, check=False, capture_output=True, text=True)

                if completed_process.stdout:
                    print(f"[INFO] Conda run STDOUT (temp script):\n{completed_process.stdout}")
                if completed_process.stderr:
                    print(f"[INFO] Conda run STDERR (temp script):\n{completed_process.stderr}")

                if completed_process.returncode != 0:
                     print(f"[ERROR] Pytest debug command (via conda run temp script) failed with return code {completed_process.returncode}.")
                # else: # Le succès sera déterminé par la présence de l'erreur pytest ou non dans la sortie.
                #    print("[SUCCESS] Pytest debug command (via conda run temp script) executed successfully.")
            
            finally:
                # Supprimer le script temporaire
                if os.path.exists(temp_script_path):
                    try:
                        os.remove(temp_script_path)
                        print(f"[INFO] Temporary script {temp_script_path} removed.")
                    except Exception as e_remove:
                        print(f"[WARNING] Failed to remove temporary script {temp_script_path}: {e_remove}")
    
        except FileNotFoundError:
            print("[ERROR] powershell command not found. Please ensure PowerShell is installed and in your PATH.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Pytest debug command failed: {e}")
            print(f"[ERROR] PowerShell STDOUT:\n{e.stdout}")
            print(f"[ERROR] PowerShell STDERR:\n{e.stderr}")
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred while running pytest with debug info: {e}")

    print("-" * 30)
    print("Setup orchestration placeholder complete.")

if __name__ == "__main__":
        # Ajout du répertoire parent de 'scripts' au PYTHONPATH pour permettre les imports relatifs si exécuté directement
        # Ceci est utile pour les tests locaux du script, mais les wrappers shell devront gérer le PYTHONPATH correctement.
        current_dir = os.path.dirname(os.path.abspath(__file__)) # type: ignore
        project_root = os.path.dirname(os.path.dirname(current_dir)) # type: ignore
        sys.path.insert(0, project_root) # S'assurer que les modules locaux sont prioritaires
    
        main()