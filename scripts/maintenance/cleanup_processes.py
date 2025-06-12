import psutil
import os
import signal
import sys

def cleanup_processes():
    """
    Finds and terminates Python and Uvicorn processes related to this project.
    """
    # Using a more robust way to get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path_marker = os.path.normpath(project_root)
    
    script_names_to_kill = ['uvicorn', 'start_webapp.py', 'unified_web_orchestrator.py', 'temp_run_playwright_js.py']
    
    processes_to_terminate = []
    print("Processus Python et Uvicorn liés au projet avant nettoyage:")
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        try:
            if not p.info.get('cmdline'):
                continue

            cmdline_str = ' '.join(p.info['cmdline']).lower()
            # Check if process is running from within the project directory or if the path is in the command line
            process_cwd = ''
            try:
                process_cwd = os.path.normpath(p.info['cwd']) if p.info['cwd'] else ''
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass # Ignore processes we can't access

            project_path_in_cmd = any(project_path_marker in os.path.normpath(L) for L in p.info['cmdline'])
            cwd_in_project = process_cwd.startswith(project_path_marker)

            if (project_path_in_cmd or cwd_in_project) and any(script_name in cmdline_str for script_name in script_names_to_kill):
                line_to_print = f"  PID: {p.pid}, Nom: {p.name()}"
                if p.name().lower() in ["python.exe", "python3.exe"]:
                    line_to_print += f", Ligne de commande: {' '.join(p.cmdline())}"
                print(line_to_print)
                processes_to_terminate.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not processes_to_terminate:
        print("Aucun processus correspondant trouvé à nettoyer.")
        return

    print("\nNettoyage des processus...")
    count = 0
    for p in processes_to_terminate:
        try:
            print(f"  Tentative de terminaison de PID {p.pid} ({p.name()})...")
            p.terminate() # More graceful than os.kill
            print(f"  Signal de terminaison envoyé à PID {p.pid}.")
            count += 1
        except psutil.NoSuchProcess:
            print(f"  Le processus {p.pid} n'existe déjà plus.")
        except Exception as e:
            print(f"  Erreur en terminant le processus {p.pid}: {e}")
            
    # Optional: wait for termination and kill if necessary
    gone, alive = psutil.wait_procs(processes_to_terminate, timeout=3)
    for p in alive:
        print(f"  Le processus {p.pid} ({p.name()}) ne s'est pas terminé, forçage...")
        try:
            p.kill()
            print(f"  Processus {p.pid} forcé à quitter.")
        except psutil.NoSuchProcess:
             print(f"  Le processus {p.pid} a disparu avant le forçage.")
        except Exception as e:
            print(f"  Erreur en forçant le processus {p.pid}: {e}")

    print(f"\n{count} processus ciblés pour la terminaison.")

if __name__ == "__main__":
    cleanup_processes()