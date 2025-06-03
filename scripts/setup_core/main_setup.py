# main_setup.py
import argparse
import sys
import os

# Placeholder pour les futurs modules
import scripts.setup_core.manage_conda_env as manage_conda_env
import scripts.setup_core.manage_portable_tools as manage_portable_tools
import scripts.setup_core.manage_project_files as manage_project_files
import scripts.setup_core.run_pip_commands as run_pip_commands

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
        conda_env_name = "epita_symbolic_ai" # Peut être rendu configurable
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

    print("-" * 30)
    print("Setup orchestration placeholder complete.")

if __name__ == "__main__":
    # Ajout du répertoire parent de 'scripts' au PYTHONPATH pour permettre les imports relatifs si exécuté directement
    # Ceci est utile pour les tests locaux du script, mais les wrappers shell devront gérer le PYTHONPATH correctement.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir)) 
    # sys.path.insert(0, project_root) # Décommenter si des imports de modules du projet sont nécessaires plus tard

    main()