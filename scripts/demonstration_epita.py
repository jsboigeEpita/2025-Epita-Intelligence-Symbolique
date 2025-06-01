"""
Script de démonstration pour le projet d'Intelligence Symbolique EPITA.

Ce script a pour but de démontrer les fonctionnalités clés du dépôt, incluant :
1. L'exécution des tests unitaires.
2. L'analyse rhétorique sur un exemple de texte clair, tentant d'utiliser les services réels `InformalAgent` et `create_llm_service`.
   Si `OPENAI_API_KEY` n'est pas configurée ou si `create_llm_service` ne peut être importé, un `MockLLMService` est utilisé.
   L'analyse des sophismes elle-même utilise un `MockFallacyDetector` pour cette démonstration afin de garantir une exécution rapide et prévisible.
3. L'analyse rhétorique sur des données chiffrées. Le script tente d'utiliser les services réels `CryptoService`
   et `DefinitionService` pour le déchiffrement. L'analyse rhétorique d'un extrait est ensuite effectuée
   par un `InformalAgent` réel (utilisant le résultat de `create_llm_service` réel si configuré, sinon un mock).
   L'analyse des sophismes elle-même utilise un `MockFallacyDetector` pour cette démonstration.
   **Correction (Sous-tâche F)**: `MockDefinitionService` retourne maintenant un objet `ExtractDefinitions` (ou son mock) correctement formé.
   **Correction (Sous-tâche I)**: L'initialisation de `RealDefinitionService` est corrigée pour inclure `config_file`.
4. La génération d'un rapport complet à partir des résultats d'analyse de l'extrait chiffré.

Prérequis importants :
- Python 3.x installé.
- Dépendances du projet : Ce script vérifie et tente d'installer `flask-cors` et `seaborn` si manquants.
  Pour les autres dépendances majeures (`pytest`, `python-dotenv`, `pandas`, `matplotlib`, `markdown`, `semantic-kernel`),
  assurez-vous qu'elles sont installées (par exemple, via `pip install -r requirements.txt` ou `pip install -e .`).
- Pour la partie "analyse de données chiffrées" et l'utilisation des services LLM réels :
    - Un fichier `argumentation_analysis/.env` doit exister et être correctement configuré.
    - Ce fichier `.env` DOIT contenir la variable `TEXT_CONFIG_PASSPHRASE` avec la passphrase correcte
      pour déchiffrer le fichier `argumentation_analysis/data/extract_sources.json.gz.enc`.
    - La variable `ENCRYPTION_KEY` doit être définie dans `argumentation_analysis/ui/config.py` pour utiliser `RealCryptoService`.
    - Pour utiliser le service LLM réel (via `create_llm_service`, pour l'analyse de texte clair et/ou l'analyse de l'extrait déchiffré),
      la variable `OPENAI_API_KEY` DOIT être définie dans le fichier `.env` ou dans l'environnement système.
      Sinon, un `MockLLMService` sera utilisé.
- Les tests unitaires (lancés par ce script) utilisent généralement des mocks pour les services externes.
- Ce script est conçu pour être exécuté depuis la racine du projet.

Comment exécuter le script :
Exécutez la commande suivante depuis la racine du projet :
python scripts/demonstration_epita.py
"""
# Imports nécessaires
print("INFO [DEMO_SCRIPT_START]: Début des imports Python standards.")
import subprocess
import json
from pathlib import Path
import os
import sys
import io
import time
import logging # Ajout du logging

# Import pour semantic_kernel, nécessaire globalement
try:
    import semantic_kernel as sk
    print("INFO [DEMO_IMPORT_DEBUG]: semantic_kernel importé.")
except ImportError:
    print("ERREUR: semantic_kernel n'a pas pu être importé. Certaines fonctionnalités seront indisponibles.")
    sk = None # Pour éviter les NameError plus tard

# Configuration du logging pour ce script
logger = logging.getLogger("demonstration_epita")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout) # Utiliser sys.stdout configuré
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# Reconfigurer sys.stdout et sys.stderr pour utiliser UTF-8
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    logger.info("sys.stdout et sys.stderr reconfigurés pour utiliser UTF-8.")
except Exception as e_reconfig_utf8:
    original_stderr = getattr(sys, '__stderr__', sys.stderr)
    if original_stderr:
        try:
            original_stderr.write(f"AVERTISSEMENT: Impossible de reconfigurer stdout/stderr en UTF-8 : {e_reconfig_utf8}\n")
            original_stderr.flush()
        except Exception:
            pass # Impossible d'afficher l'avertissement

# Détermination de la racine du projet
# __file__ est le chemin du script actuel (demonstration_epita.py)
current_script_path = Path(__file__).resolve()
# project_root est le répertoire parent de 'scripts'
project_root = current_script_path.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
logger.info(f"Racine du projet calculée : {project_root}")
logger.debug(f"Current sys.path: {sys.path}")

# Import du module de bootstrap
try:
    from project_core.bootstrap import initialize_project_environment, ProjectContext
    logger.info("Module de bootstrap importé avec succès.")
except ImportError as e:
    logger.critical(f"ERREUR CRITIQUE: Impossible d'importer le module de bootstrap 'project_core.bootstrap'. {e}")
    logger.critical("Assurez-vous que project_core/bootstrap.py existe et que project_root est correctement dans sys.path.")
    sys.exit(1) # Arrêter si le bootstrap n'est pas là

# Imports des modèles de données (nécessaires pour typer et instancier dans la démo)
try:
    from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
    logger.info("Modèles d'extrait (ExtractDefinitions, etc.) importés.")
except ImportError as e:
    logger.error(f"AVERTISSEMENT: Impossible d'importer les modèles d'extrait: {e}. Certaines parties de la démo pourraient échouer.")
    ExtractDefinitions, SourceDefinition, Extract = None, None, None


# La vérification et l'installation des dépendances peuvent rester,
# car elles concernent l'environnement d'exécution de base du script.
def check_and_install_dependencies():
    """
    Vérifie la présence des packages listés (`flask-cors`, `seaborn`, `semantic-kernel`) et tente de les installer s'ils sont manquants.
    Les autres dépendances majeures sont supposées être installées.
    """
    print("\n--- Vérification et installation des dépendances (flask-cors, seaborn, semantic-kernel) ---")
    dependencies = ["flask-cors", "seaborn", "semantic-kernel", "markdown"]
    for package_name in dependencies:
        try:
            module_name = package_name.replace("-", "_")
            __import__(module_name)
            print(f"INFO: Le package '{package_name}' (module '{module_name}') est déjà installé.")
        except ImportError:
            print(f"AVERTISSEMENT: Le package '{package_name}' (module '{module_name}') n'est pas trouvé. Tentative d'installation...")
            try:
                # Utiliser capture_output=True et text=True pour subprocess.run
                # S'assurer que l'encodage est géré pour la sortie du subprocess
                # Ajout d'un timeout de 300 secondes pour l'installation
                print(f"INFO: Tentative d'installation de '{package_name}' avec un timeout de 300 secondes...")
                pip_result = subprocess.run([sys.executable, "-m", "pip", "install", package_name], 
                                            check=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
                print(f"SUCCÈS: Le package '{package_name}' a été installé.")
                if pip_result.stdout:
                    print(f"Sortie pip (stdout):\n{pip_result.stdout}")
            except subprocess.TimeoutExpired:
                print(f"ERREUR: L'installation de '{package_name}' a dépassé le timeout de 300 secondes.")
                print(f"Veuillez vérifier votre connexion internet et installer '{package_name}' manuellement.")
            except subprocess.CalledProcessError as e:
                print(f"ERREUR: Échec de l'installation de '{package_name}'. Code de retour : {e.returncode}")
                # e.stdout et e.stderr sont déjà des chaînes si text=True a été utilisé, ou des bytes sinon.
                # Si text=True n'était pas utilisé (ou si on veut être ultra-prudent), on décode.
                # Ici, on suppose que si text=True est utilisé dans l'appel original, e.stdout/stderr sont des str.
                # Si on veut être sûr, on peut décoder comme pour la sortie pytest.
                # Pour simplifier, on les traite comme des chaînes (résultat de text=True).
                if e.stdout:
                    print(f"Sortie pip (stdout):\n{e.stdout}")
                if e.stderr:
                    print(f"Sortie pip (stderr):\n{e.stderr}")
                print(f"Veuillez vérifier votre connexion internet et installer '{package_name}' manuellement (ex: pip install {package_name}).")
            except FileNotFoundError:
                print(f"ERREUR: La commande '{sys.executable} -m pip' n'a pas été trouvée. Assurez-vous que pip est installé et accessible dans l'environnement Python actuel.")
                print(f"Veuillez installer '{package_name}' manuellement.")
            except Exception as e:
                print(f"ERREUR: Une erreur inattendue est survenue lors de la tentative d'installation de '{package_name}': {e}")
                print(f"Veuillez installer '{package_name}' manuellement.")
        except Exception as e:
            print(f"ERREUR: Une erreur inattendue est survenue lors de la vérification de '{package_name}': {e}")


def run_unit_tests():
    print("\n--- Exécution des tests unitaires ---")
    print("INFO: Les tests unitaires utilisent typiquement des mocks pour isoler le code testé.")
    start_time_tests = time.time()
    print(f"INFO: Début de l'exécution des tests unitaires : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_tests))}")
    try:
        # MODIFICATION 1: Capturer en bytes (retrait de text=True, encoding, errors)
        # Ajout d'un timeout de 900 secondes (15 minutes)
        print("INFO: Exécution de pytest avec un timeout de 900 secondes (15 minutes)...")
        pytest_process = subprocess.run([sys.executable, "-m", "pytest"], capture_output=True, check=False, timeout=900) # Timeout augmenté
        
        end_time_tests = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_tests))}")
        print(f"INFO: Tests unitaires exécutés en {end_time_tests - start_time_tests:.2f} secondes.")

        # MODIFICATION 2: Décodage robuste de stdout et stderr
        pytest_stdout_str = ""
        pytest_stderr_str = ""

        if pytest_process.stdout:
            try:
                pytest_stdout_str = pytest_process.stdout.decode('utf-8', errors='replace')
            except UnicodeDecodeError as e_decode_utf8:
                print(f"AVERTISSEMENT: Échec du décodage UTF-8 pour stdout: {e_decode_utf8}. Tentative avec latin-1.")
                try:
                    pytest_stdout_str = pytest_process.stdout.decode('latin-1', errors='replace')
                except UnicodeDecodeError as e_decode_latin1:
                    print(f"ERREUR: Échec du décodage latin-1 pour stdout après échec UTF-8: {e_decode_latin1}.")
                    # Représentation des bytes si tout échoue
                    pytest_stdout_str = f"Impossible de décoder stdout. Données brutes (repr): {repr(pytest_process.stdout)}"
            except Exception as e_decode_other_stdout:
                print(f"ERREUR: Erreur inattendue lors du décodage de stdout: {e_decode_other_stdout}")
                pytest_stdout_str = f"Erreur inattendue lors du décodage de stdout. Données brutes (repr): {repr(pytest_process.stdout)}"


        if pytest_process.stderr:
            try:
                pytest_stderr_str = pytest_process.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError as e_decode_utf8_err:
                print(f"AVERTISSEMENT: Échec du décodage UTF-8 pour stderr: {e_decode_utf8_err}. Tentative avec latin-1.")
                try:
                    pytest_stderr_str = pytest_process.stderr.decode('latin-1', errors='replace')
                except UnicodeDecodeError as e_decode_latin1_err:
                    print(f"ERREUR: Échec du décodage latin-1 pour stderr après échec UTF-8: {e_decode_latin1_err}.")
                    pytest_stderr_str = f"Impossible de décoder stderr. Données brutes (repr): {repr(pytest_process.stderr)}"
            except Exception as e_decode_other_stderr:
                 print(f"ERREUR: Erreur inattendue lors du décodage de stderr: {e_decode_other_stderr}")
                 pytest_stderr_str = f"Erreur inattendue lors du décodage de stderr. Données brutes (repr): {repr(pytest_process.stderr)}"

        print("\nRésultat de l'exécution de pytest:")

        # MODIFICATION 3: Impression de stdout (try-except commenté)
        if pytest_stdout_str:
            print("\n--- Sortie Standard Pytest ---")
            # try:
            print(pytest_stdout_str)
            # except UnicodeEncodeError:
            #     print("(Encodage forcé pour la sortie standard en raison d'une UnicodeEncodeError)")
            #     output_encoding_stdout = sys.stdout.encoding if sys.stdout.encoding else 'utf-8'
            #     print(pytest_stdout_str.encode(output_encoding_stdout, errors='replace').decode(output_encoding_stdout, errors='ignore'))
            # finally:
            print("--- Fin Sortie Standard Pytest ---")
        
        # MODIFICATION 4: Impression de stderr (try-except commenté)
        if pytest_stderr_str:
            print("\n--- Sortie d'Erreur Pytest ---")
            # try:
            print(pytest_stderr_str)
            # except UnicodeEncodeError:
            #     print("(Encodage forcé pour la sortie d'erreur en raison d'une UnicodeEncodeError)")
            #     output_encoding_stderr = sys.stderr.encoding if sys.stderr.encoding else 'utf-8'
            #     print(pytest_stderr_str.encode(output_encoding_stderr, errors='replace').decode(output_encoding_stderr, errors='ignore'))
            # finally:
            print("--- Fin Sortie d'Erreur Pytest ---")

        # MODIFICATION 5: Utiliser pytest_process.returncode et pytest_stdout_str pour le résumé
        if pytest_process.returncode == 0:
            print("\nSUCCÈS: Tests unitaires réussis !")
        else:
            print(f"\nAVERTISSEMENT: Échec des tests unitaires ou certains tests ont échoué (code de retour : {pytest_process.returncode}).")
            
            summary_lines = []
            if pytest_stdout_str: 
                try:
                    keywords = ["collected", "passed", "failed", "error", "skipped", "xfailed", "xpassed", "short test summary info", "===="]
                    summary_lines = [line for line in pytest_stdout_str.splitlines() if any(keyword in line.lower() for keyword in keywords)]
                except Exception as e_split: 
                    print(f"AVERTISSEMENT: Erreur lors du découpage de la sortie standard pour le résumé: {e_split}")
                    summary_lines = ["Erreur lors de l'extraction du résumé."] # Fournir un message d'erreur dans le résumé

            if summary_lines:
                summary_to_print = "\n".join(summary_lines)
                print("\n--- Résumé des tests (extrait de la sortie) ---")
                # try:
                print(summary_to_print)
                # except UnicodeEncodeError:
                #     print("(Encodage forcé pour le résumé en raison d'une UnicodeEncodeError)")
                #     output_encoding_summary = sys.stdout.encoding if sys.stdout.encoding else 'utf-8'
                #     print(summary_to_print.encode(output_encoding_summary, errors='replace').decode(output_encoding_summary, errors='ignore'))
                # finally:
                print("--- Fin Résumé des tests ---")
            elif pytest_stdout_str : # Si stdout n'est pas vide mais aucun résumé pertinent
                 print("Aucun résumé pertinent trouvé dans la sortie de pytest.")
            else: # Si pytest_stdout_str est vide
                print("Impossible d'extraire un résumé : la sortie standard de pytest était vide.")
    except subprocess.TimeoutExpired:
        print("ERREUR: L'exécution de pytest a dépassé le timeout de 900 secondes (15 minutes).")
        print("Cela peut indiquer un problème dans les tests (boucle infinie, attente indéfinie), un environnement très lent, ou des tests particulièrement longs.")
        print("Si ce problème persiste, essayez d'exécuter 'pytest -v' manuellement pour identifier les tests lents ou bloquants.")
        end_time_tests_timeout = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires (timeout) : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_tests_timeout))}")
        print(f"INFO: Tests unitaires (tentative) exécutés en {end_time_tests_timeout - start_time_tests:.2f} secondes avant timeout.")
    except FileNotFoundError:
        print("ERREUR: La commande 'pytest' n'a pas été trouvée. Assurez-vous que pytest est installé et dans votre PATH.")
        end_time_tests_error = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires (erreur FileNotFoundError) : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_tests_error))}")
        print(f"INFO: Tests unitaires (tentative) exécutés en {end_time_tests_error - start_time_tests:.2f} secondes.")
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors de l'exécution des tests : {e}")
        import traceback
        traceback.print_exc()
        end_time_tests_exception = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires (erreur Exception) : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_tests_exception))}")
        print(f"INFO: Tests unitaires (tentative) exécutés en {end_time_tests_exception - start_time_tests:.2f} secondes.")


def analyze_clear_text_example(project_context: ProjectContext, example_file_path_str: str):
    logger.info(f"\n--- Analyse du fichier texte : {example_file_path_str} ---")

    if not project_context.informal_agent:
        logger.error("InformalAgent non initialisé dans project_context. Impossible d'analyser le texte clair.")
        return
    
    # Utiliser project_root_path depuis le contexte pour construire le chemin absolu
    # si example_file_path_str est relatif.
    # Si example_file_path_str est déjà absolu, Path le gérera.
    # Le script original utilisait project_root global.
    # Ici, on s'assure d'utiliser celui du contexte ou le project_root global s'il est défini.
    current_project_root_path = project_context.project_root_path if project_context.project_root_path else Path(project_root)

    file_path = Path(example_file_path_str)
    if not file_path.is_absolute():
        file_path = current_project_root_path / example_file_path_str


    try:
        if not file_path.is_file():
            logger.error(f"Le fichier d'exemple '{file_path}' n'a pas été trouvé.")
            default_content = "Ceci est un texte d'exemple pour l'analyse de sophismes. L'argument de mon adversaire est ridicule, il doit être idiot. De plus, tout le monde sait que j'ai raison."
            logger.info(f"Création d'un fichier d'exemple à '{file_path}' avec contenu par défaut.")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(default_content)
        
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        logger.info(f"Contenu du fichier (premiers 200 caractères) :\n{text_content[:200]}...\n")
        
        agent_instance = project_context.informal_agent
        analysis_description = f"InformalAgent (type: {type(agent_instance).__name__})"
        if project_context.llm_service:
            analysis_description += f" avec LLM Service (type: {type(project_context.llm_service).__name__})"
        else:
            analysis_description += " sans LLM Service configuré via bootstrap (l'agent peut utiliser un fallback interne ou échouer)."

        logger.info(f"Utilisation de {analysis_description} pour l'analyse.")
            
        try:
            start_time_analyze_clear = time.time()
            logger.info(f"Début de l'analyse des sophismes (texte clair) : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_analyze_clear))}")
            
            # L'InformalAgent initialisé par le bootstrap devrait avoir son kernel et LLM service déjà configurés.
            # La méthode analyze_fallacies devrait fonctionner directement.
            analysis_results = agent_instance.analyze_fallacies(text_content)
            
            end_time_analyze_clear = time.time()
            logger.info(f"Fin de l'analyse des sophismes (texte clair) : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_analyze_clear))}")
            logger.info(f"Analyse des sophismes (texte clair) effectuée en {end_time_analyze_clear - start_time_analyze_clear:.2f} secondes.")

            logger.info(f"Résultats de l'analyse des sophismes ({analysis_description}) :")
            try:
                # Utiliser logger.info pour la sortie JSON pour la cohérence
                logger.info(json.dumps(analysis_results, indent=4, ensure_ascii=False))
            except TypeError:
                logger.warning(f"Les résultats de l'analyse ne sont pas directement sérialisables en JSON. Affichage brut : {analysis_results}")
        
        except Exception as e_analyze:
            logger.error(f"ERREUR lors de l'appel à agent_instance.analyze_fallacies pour le texte clair : {e_analyze}", exc_info=True)

    except Exception as e:
        logger.error(f"Une erreur est survenue lors de l'analyse du fichier '{file_path}' : {e}", exc_info=True)


def analyze_encrypted_data(project_context: ProjectContext) -> str | None:
    logger.info("\n--- Analyse des données chiffrées ---")
    
    if not project_context.crypto_service:
        logger.error("CryptoService non initialisé dans project_context. Impossible de déchiffrer.")
        return None
    if not project_context.definition_service:
        logger.error("DefinitionService non initialisé dans project_context. Impossible de charger les définitions.")
        return None
    if not project_context.informal_agent:
        logger.error("InformalAgent non initialisé dans project_context. Impossible d'analyser.")
        return None
    if Extract is None or ExtractDefinitions is None: # Vérifier si les modèles ont été importés
        logger.error("Les modèles Extract/ExtractDefinitions n'ont pas été importés. Impossible de traiter les données.")
        return None

    analysis_results_list = []
    current_project_root_path = project_context.project_root_path if project_context.project_root_path else Path(project_root)
    
    # Le chemin du fichier de configuration est géré par DefinitionService lors de son initialisation dans bootstrap
    # abs_definitions_file_path = current_project_root_path / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
    # logger.info(f"Utilisation du DefinitionService configuré par bootstrap (qui devrait utiliser {abs_definitions_file_path})")

    try:
        start_time_load_defs = time.time()
        logger.info(f"Début du chargement des définitions d'extraits via DefinitionService du contexte: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_load_defs))}")
        
        extract_definitions_obj = project_context.definition_service.load_definitions()
        
        end_time_load_defs = time.time()
        logger.info(f"Fin du chargement des définitions d'extraits : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_load_defs))}")
        logger.info(f"Définitions d'extraits chargées en {end_time_load_defs - start_time_load_defs:.2f} secondes.")
        
        # La structure de extract_definitions_obj peut avoir changé.
        # Le mock original avait .extracts directement. Le réel pourrait avoir .sources puis .extracts.
        # Le mock dans bootstrap.py pour DefinitionService retourne un objet ExtractDefinitions avec un attribut 'extracts'.
        # Si le service réel retourne une structure avec 'sources', il faudra adapter.
        # Pour l'instant, on suppose que extract_definitions_obj.extracts est la liste des extraits.
        
        # Tentative de gestion des deux structures (directement .extracts ou .sources[0].extracts)
        extracts_to_process = []
        if hasattr(extract_definitions_obj, 'extracts') and isinstance(extract_definitions_obj.extracts, list):
            extracts_to_process = extract_definitions_obj.extracts
            logger.info(f"{len(extracts_to_process)} extraits trouvés directement dans extract_definitions_obj.extracts.")
        elif hasattr(extract_definitions_obj, 'sources') and isinstance(extract_definitions_obj.sources, list) and extract_definitions_obj.sources:
            first_source = extract_definitions_obj.sources[0]
            if hasattr(first_source, 'extracts') and isinstance(first_source.extracts, list):
                extracts_to_process = first_source.extracts
                logger.info(f"{len(extracts_to_process)} extraits trouvés dans la première source (extract_definitions_obj.sources[0].extracts).")
            else:
                logger.warning("extract_definitions_obj.sources[0] ne contient pas d'attribut 'extracts' de type liste.")
        else:
            logger.error("Aucun extrait trouvé dans l'objet extract_definitions. Structure attendue : .extracts ou .sources[0].extracts.")
            logger.debug(f"Type de extract_definitions_obj: {type(extract_definitions_obj)}")
            if hasattr(extract_definitions_obj, 'extracts'): logger.debug(f"Type de .extracts: {type(extract_definitions_obj.extracts)}")
            if hasattr(extract_definitions_obj, 'sources'): logger.debug(f"Type de .sources: {type(extract_definitions_obj.sources)}")
            return None

        if not extracts_to_process:
            logger.info("Aucun extrait à analyser.")
            return None

        selected_extract = extracts_to_process[0] # Analyse du premier extrait pour la démo
        
        # Les attributs de 'selected_extract' devraient correspondre à la classe Extract
        # (soit réelle, soit le mock si l'import réel a échoué dans bootstrap)
        extract_id = getattr(selected_extract, 'id', getattr(selected_extract, 'extract_name', 'N/A_ID'))
        text_content_extract = getattr(selected_extract, 'full_text', '') # MODIFIÉ ICI
        extract_title = getattr(selected_extract, 'title', 'N/A_Title')

        logger.info(f"\n--- Analyse rhétorique de l'extrait déchiffré (ID: {extract_id}, Titre: {extract_title}) ---")
        logger.info(f"Texte de l'extrait sélectionné (premiers 200 chars):\n{text_content_extract[:200]}...")

        agent_instance_encrypted = project_context.informal_agent
        analysis_description_encrypted = f"InformalAgent (type: {type(agent_instance_encrypted).__name__})"
        if project_context.llm_service:
            analysis_description_encrypted += f" avec LLM Service (type: {type(project_context.llm_service).__name__})"
        else:
            analysis_description_encrypted += " sans LLM Service configuré (l'agent peut utiliser un fallback ou échouer)."
        logger.info(f"Utilisation de {analysis_description_encrypted} pour l'analyse de l'extrait.")
            
        try:
            start_time_analyze_encrypted = time.time()
            logger.info(f"Début de l'analyse des sophismes (extrait déchiffré) : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_analyze_encrypted))}")
            
            real_analysis_data = agent_instance_encrypted.analyze_fallacies(text_content_extract)
            
            end_time_analyze_encrypted = time.time()
            logger.info(f"Fin de l'analyse des sophismes (extrait déchiffré) : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_analyze_encrypted))}")
            logger.info(f"Analyse des sophismes (extrait déchiffré) effectuée en {end_time_analyze_encrypted - start_time_analyze_encrypted:.2f} secondes.")

            structured_analysis_result = {
                "extract_id": extract_id,
                "title": extract_title,
                "analysis_type": f"Rhetorical Analysis ({analysis_description_encrypted})",
                "analysis_details": real_analysis_data
            }
            analysis_results_list.append(structured_analysis_result)

            logger.info("\nRésultat de l'analyse de l'extrait (formaté pour sauvegarde) :")
            logger.info(json.dumps(analysis_results_list, indent=4, ensure_ascii=False))
        
        except Exception as e_analyze_enc:
            logger.error(f"ERREUR lors de l'appel à agent_instance_encrypted.analyze_fallacies : {e_analyze_enc}", exc_info=True)

        results_dir = current_project_root_path / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        analysis_output_path = results_dir / "analysis_encrypted_extract_demo_refactored.json"
        with open(analysis_output_path, "w", encoding="utf-8") as f:
            try:
                json.dump(analysis_results_list, f, indent=4, ensure_ascii=False)
            except TypeError:
                f.write(str(analysis_results_list))
                logger.warning(f"Le résultat de l'analyse chiffrée n'était pas sérialisable en JSON, sauvegardé comme chaîne.")
        logger.info(f"\nRésultat de l'analyse sauvegardé dans : {analysis_output_path.resolve()}")
        
        return str(analysis_output_path.resolve())

    except FileNotFoundError as e:
        logger.error(f"ERREUR Fichier non trouvé : {e}", exc_info=True)
    except KeyError as e:
        logger.error(f"ERREUR Variable d'environnement manquante : {e}", exc_info=True)
    except json.JSONDecodeError as e:
        logger.error(f"ERREUR de décodage JSON : {e}", exc_info=True)
    except AttributeError as e:
        logger.error(f"ERREUR d'attribut : {e}. Problème avec la structure des objets.", exc_info=True)
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue lors de l'analyse des données chiffrées : {e}", exc_info=True)
    return None


def generate_report_from_analysis(project_context: ProjectContext, analysis_json_path_str: str):
    logger.info(f"\n--- Génération du rapport à partir de : {analysis_json_path_str} ---")
    
    current_project_root_path = project_context.project_root_path if project_context.project_root_path else Path(project_root)
    report_script_path = current_project_root_path / "scripts" / "generate_comprehensive_report.py"
    
    analysis_file_path = Path(analysis_json_path_str) # Doit être un chemin absolu ou relatif au CWD

    if not report_script_path.exists():
        logger.error(f"Le script de génération de rapport '{report_script_path}' n'a pas été trouvé.")
        return

    if not analysis_file_path.exists():
        logger.error(f"Le fichier de résultats d'analyse '{analysis_file_path}' n'a pas été trouvé.")
        return

    start_time_report_gen = time.time()
    logger.info(f"Début de la génération du rapport : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_report_gen))}")
    try:
        command = [
            sys.executable, str(report_script_path.resolve()),
            "--advanced-results", str(analysis_file_path.resolve())
        ]
        logger.info(f"Exécution de la commande : {' '.join(command)}")
        
        logger.info("Exécution du script de génération de rapport avec un timeout de 300 secondes...")
        report_process = subprocess.run(command, capture_output=True, check=False, cwd=str(current_project_root_path), timeout=300)
 
        report_stdout_str = ""
        report_stderr_str = ""

        if report_process.stdout:
            try:
                report_stdout_str = report_process.stdout.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                try:
                    report_stdout_str = report_process.stdout.decode('latin-1', errors='replace')
                except:
                    report_stdout_str = f"Impossible de décoder stdout du script de rapport. Données brutes (repr): {repr(report_process.stdout)}"
        
        if report_process.stderr:
            try:
                report_stderr_str = report_process.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                try:
                    report_stderr_str = report_process.stderr.decode('latin-1', errors='replace')
                except:
                    report_stderr_str = f"Impossible de décoder stderr du script de rapport. Données brutes (repr): {repr(report_process.stderr)}"

        logger.info("\nRésultat de la génération du rapport :")
        if report_stdout_str:
            logger.info("\n--- Sortie Standard du script de rapport ---")
            logger.info(report_stdout_str)
            logger.info("--- Fin Sortie Standard du script de rapport ---")
        
        if report_stderr_str:
            logger.error("\n--- Sortie d'Erreur du script de rapport ---")
            logger.error(report_stderr_str)
            logger.error("--- Fin Sortie d'Erreur du script de rapport ---")
        
        if report_process.returncode == 0:
            logger.info("\nSUCCÈS: Génération du rapport terminée.")
            logger.info(f"Les rapports devraient être disponibles dans le dossier '{current_project_root_path / 'results' / 'reports' / 'comprehensive'}'")
        else:
            logger.error(f"\nÉCHEC: La génération du rapport a échoué (code de retour : {report_process.returncode}).")
            logger.error("Vérifiez les logs ci-dessus et les dépendances du script de rapport.")

    except subprocess.TimeoutExpired:
        logger.error("ERREUR: L'exécution du script de génération de rapport a dépassé le timeout de 300 secondes.")
    except FileNotFoundError:
        logger.error(f"ERREUR: L'interpréteur Python ('{sys.executable}') ou le script de rapport n'a pas été trouvé.")
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue lors de la génération du rapport : {e}", exc_info=True)
    
    end_time_report_gen = time.time()
    logger.info(f"Fin de la génération du rapport : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_report_gen))}")
    logger.info(f"Génération du rapport effectuée en {end_time_report_gen - start_time_report_gen:.2f} secondes.")


if __name__ == "__main__":
    logger.info("=== Début du script de démonstration EPITA (Refactorisé) ===")
    start_time_script = time.time()
    logger.info(f"Heure de début du script : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_script))}")

    # Initialisation de l'environnement via le bootstrap
    # Le bootstrap s'occupe du .env, de la JVM, et des services principaux.
    # project_root est déjà défini globalement dans ce script.
    logger.info("Initialisation de l'environnement du projet via le module de bootstrap...")
    # Passer project_root explicitement au bootstrap pour qu'il sache où il est.
    # Le chemin vers .env sera déduit par le bootstrap à partir de ce root_path_str.
    project_context = initialize_project_environment(root_path_str=str(project_root))

    if not project_context:
        logger.critical("Échec de l'initialisation du contexte du projet. Arrêt du script.")
        sys.exit(1)

    logger.info(f"Contexte du projet initialisé. Racine du projet utilisée: {project_context.project_root_path}")
    logger.info(f"JVM initialisée par bootstrap: {project_context.jvm_initialized}")

    # 1. Vérification des dépendances (peut rester, car c'est pour l'environnement Python de base)
    logger.info("Appel de check_and_install_dependencies()...")
    check_and_install_dependencies()
    logger.info("Fin de check_and_install_dependencies().")

    # 2. Exécution des tests unitaires (peut rester)
    logger.info("Appel de run_unit_tests()...")
    run_unit_tests() # Cette fonction utilise le project_root global
    logger.info("Fin de run_unit_tests().")

    # 3. Analyse de texte clair
    # Le chemin vers exemple_sophisme.txt est relatif à la racine du projet.
    example_clear_text_file = "examples/exemple_sophisme.txt" # Relatif à project_root
    logger.info(f"Appel de analyze_clear_text_example() avec le fichier : {example_clear_text_file}...")
    analyze_clear_text_example(project_context, example_clear_text_file)
    logger.info("Fin de analyze_clear_text_example().")

    # 4. Analyse de données chiffrées
    logger.info("Appel de analyze_encrypted_data()...")
    encrypted_analysis_output_file_path = analyze_encrypted_data(project_context)
    logger.info("Fin de analyze_encrypted_data().")

    # 5. Génération de rapport
    if encrypted_analysis_output_file_path:
        logger.info(f"Appel de generate_report_from_analysis() avec le fichier : {encrypted_analysis_output_file_path}...")
        generate_report_from_analysis(project_context, encrypted_analysis_output_file_path)
        logger.info("Fin de generate_report_from_analysis().")
    else:
        logger.warning("\nLa génération de rapport à partir des données chiffrées a été sautée (pas de fichier de résultat).")

    # 6. TODO: Interaction avec Tweety (à ajouter pour être exhaustif)
    # Cette partie nécessitera d'utiliser jpype et les classes Tweety via le project_context.jvm_initialized
    # et potentiellement des classes chargées dans project_context.tweety_classes.
    logger.info("\n--- Démonstration de l'interaction avec Tweety (TODO) ---")
    if project_context.jvm_initialized:
        logger.info("La JVM est initialisée. Une interaction basique avec Tweety pourrait être ajoutée ici.")
        try:
            import jpype
            # Exemple simple: charger une classe Tweety et l'afficher
            if jpype.isJVMStarted(): # Double vérification
                PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
                parser_instance = PlParser()
                logger.info(f"Instance de PlParser créée avec succès via JPype: {parser_instance}")
                
                # Parser une formule simple
                formula_str = "a & b"
                parsed_formula = parser_instance.parseFormula(jpype.JString(formula_str))
                logger.info(f"Formule Tweety '{formula_str}' parsée en: {parsed_formula.toString()}")
                
                # Afficher les atomes
                atoms_set = parsed_formula.getAtoms() # java.util.Set
                py_atoms_list = [str(atom) for atom in atoms_set]
                logger.info(f"Atomes dans la formule: {py_atoms_list}")

            else:
                logger.warning("JVM initialisée par bootstrap, mais jpype.isJVMStarted() est False ici. Étrange.")
        except Exception as e_tweety:
            logger.error(f"Erreur lors de la démonstration Tweety : {e_tweety}", exc_info=True)
    else:
        logger.warning("JVM non initialisée, la démonstration Tweety est sautée.")


    end_time_script = time.time()
    logger.info(f"\nHeure de fin du script : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_script))}")
    logger.info(f"Durée totale d'exécution du script : {end_time_script - start_time_script:.2f} secondes.")
    logger.info("\n=== Fin du script de démonstration EPITA (Refactorisé) ===")