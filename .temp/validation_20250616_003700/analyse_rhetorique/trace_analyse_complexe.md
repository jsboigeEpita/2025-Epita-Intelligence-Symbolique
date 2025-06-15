conda.exe : 01:23:28 [INFO] [root] Logging configuré pour l'orchestration.
Au caractère C:\Tools\miniconda3\shell\condabin\Conda.psm1:153 : 17
+ ...             & $Env:CONDA_EXE $Env:_CE_M $Env:_CE_CONDA $Command @Othe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (01:23:28 [INFO]...'orchestration.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
01:23:28 [INFO] [root] .env chargé: True
01:23:28 [INFO] [argumentation_analysis] Package 'argumentation_analysis' chargé.
01:23:28 [DEBUG] [argumentation_analysis.core.shared_state] Module core.shared_state chargé.
01:23:30 [INFO] [Orchestration.LLM] <<<<< MODULE llm_service.py LOADED >>>>>
01:23:30 [DEBUG] [argumentation_analysis.core.llm_service] Module core.llm_service chargé.
01:23:30 [INFO] [Orchestration.JPype] LIBS_DIR défini sur (primaire): D:\2025-Epita-Intelligence-Symbolique\libs\tweety
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\argumentation_analysis\config
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\argumentation_analysis\data
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\libs
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\libs
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\libs\tweety
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\libs\tweety\native
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\results
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\portable_jdk
01:23:30 [DEBUG] [Paths] Répertoire assuré: D:\2025-Epita-Intelligence-Symbolique\_temp
01:23:30 [INFO] [root] Initialisation de la JVM...
01:23:30 [INFO] [Orchestration.JPype] JVM_SETUP: initialize_jvm appelée. isJVMStarted au début: False
01:23:30 [INFO] [Orchestration.JPype] JVM_SETUP: _JVM_WAS_SHUTDOWN: False
01:23:30 [INFO] [Orchestration.JPype] JVM_SETUP: _JVM_INITIALIZED_THIS_SESSION: False
01:23:30 [INFO] [Orchestration.JPype] JVM_SETUP: _SESSION_FIXTURE_OWNS_JVM: False
01:23:30 [INFO] [Orchestration.JPype] JVM_SETUP: Version de JPype: 1.5.2
01:23:30 [INFO] [Orchestration.JPype] Classpath construit avec 0 JAR(s) depuis 
'D:\2025-Epita-Intelligence-Symbolique\libs'.
01:23:30 [INFO] [Orchestration.JPype] Classpath configuré avec 0 JARs (JPype 1.5.2)
01:23:30 [ERROR] [Orchestration.JPype] (ERREUR) Aucun JAR trouvé pour le classpath. Démarrage annulé.
01:23:30 [WARNING] [root] ⚠️ JVM n'a pas pu être initialisée. L'agent PropositionalLogicAgent ne fonctionnera pas.
01:23:30 [INFO] [root] Création du service LLM...
01:23:30 [CRITICAL] [Orchestration.LLM] <<<<< get_llm_service FUNCTION CALLED >>>>>
01:23:30 [INFO] [Orchestration.LLM] --- Configuration du Service LLM (global_llm_service) ---
01:23:30 [INFO] [Orchestration.LLM] Project root determined from __file__: D:\2025-Epita-Intelligence-Symbolique
01:23:30 [INFO] [Orchestration.LLM] Attempting to load .env from absolute path: 
D:\2025-Epita-Intelligence-Symbolique\.env
01:23:30 [INFO] [Orchestration.LLM] load_dotenv success with absolute path 
'D:\2025-Epita-Intelligence-Symbolique\.env': True
01:23:30 [INFO] [Orchestration.LLM] Value of api_key directly from os.getenv: 'sk-proj-xZdmcBNk2VEYItYduhjiJHaIGsp0eQC4
yLcCVsM98Tk7EvP3shBwof1h5a0KRxijn7836W7C6IT3BlbkFJEiXMRhp-ovTixVjK09yBWLU8d-PE4NdWv85WvSPIH8PpNIbHSRHUDtw0CRnWK9_lXRVtz
nQn0A'
01:23:30 [INFO] [Orchestration.LLM] OpenAI API Key (first 5, last 5): sk-pr...nQn0A
01:23:30 [INFO] [Orchestration.LLM] Configuration détectée - base_url: None, endpoint: None
01:23:30 [INFO] [Orchestration.LLM] Configuration Service: OpenAIChatCompletion...
01:23:30 [INFO] [Orchestration.LLM] Service LLM OpenAI (gpt-4o-mini) créé avec ID 'global_llm_service' et HTTP client 
personnalisé.
01:23:30 [INFO] [root] [OK] Service LLM créé avec succès (ID: global_llm_service).
01:23:30 [INFO] [root] Texte chargé depuis examples\texts\texte_analyse_temp.txt (193 caractères)
01:23:30 [INFO] [root] Lancement de l'orchestration sur un texte de 193 caractères...
01:23:30 [DEBUG] [argumentation_analysis.ui] Package UI chargé.
01:23:30 [DEBUG] [argumentation_analysis.utils] Package 'argumentation_analysis.utils' initialisé.
01:23:30 [INFO] [App.ProjectCore.FileLoaders] Utilitaires de chargement de fichiers (FileLoaders) définis.
01:23:30 [INFO] [App.ProjectCore.FileSavers] Utilitaires de sauvegarde de fichiers (FileSavers) définis.
01:23:30 [INFO] [App.ProjectCore.MarkdownUtils] Utilitaires Markdown (MarkdownUtils) définis.
01:23:30 [INFO] [App.ProjectCore.PathOperations] Utilitaires d'opérations sur les chemins (PathOperations) définis.
01:23:30 [INFO] [argumentation_analysis.utils.core_utils.file_utils] Module principal des utilitaires de fichiers 
(file_utils.py) initialisé et sous-modules importés.
01:23:30 [INFO] [App.UI.Config] Utilisation de la phrase secrète fixe pour la dérivation de la clé.
01:23:30 [INFO] [App.UI.Config] [OK] Phrase secrète définie sur "Propaganda". Dérivation de la clé...
01:23:30 [INFO] [App.UI.Config] [OK] Clé de chiffrement dérivée et encodée.
01:23:30 [INFO] [App.UI.Config] TIKA_SERVER_ENDPOINT depuis .env (nettoyé): 'https://tika.open-webui.myia.io/'
01:23:30 [INFO] [App.UI.Config] URL du serveur Tika: https://tika.open-webui.myia.io/tika
01:23:30 [INFO] [App.UI.Config] Cache répertoire assuré : D:\2025-Epita-Intelligence-Symbolique\_temp\text_cache
01:23:30 [INFO] [App.UI.Config] Répertoire config UI assuré : 
D:\2025-Epita-Intelligence-Symbolique\argumentation_analysis\data
01:23:30 [INFO] [App.UI.Config] Répertoire temporaire assuré : 
D:\2025-Epita-Intelligence-Symbolique\_temp\temp_downloads
01:23:30 [INFO] [App.UI.Config] Config UI initialisée. EXTRACT_SOURCES est sur DEFAULT_EXTRACT_SOURCES. Le chargement 
dynamique est délégué.
01:23:30 [INFO] [App.UI.Config] Module config.py initialisé. 1 sources par défaut disponibles dans EXTRACT_SOURCES.
01:23:30 [INFO] [App.UI.Config] PROJECT_ROOT exporté: D:\2025-Epita-Intelligence-Symbolique
01:23:30 [INFO] [App.UI.CacheUtils] Utilitaires de cache UI définis.
01:23:30 [INFO] [App.UI.FetchUtils] Utilitaires de fetch UI définis.
01:23:30 [INFO] [App.UI.VerificationUtils] Utilitaires de vérification UI définis.
01:23:30 [INFO] [App.UI.Utils] Module principal des utilitaires UI (utils.py) initialisé et sous-modules importés.
01:23:30 [INFO] [Services.CacheService] Répertoire de cache initialisé: 
D:\2025-Epita-Intelligence-Symbolique\_temp\text_cache
01:23:30 [INFO] [Services.FetchService] FetchService initialisé avec Tika URL: https://tika.open-webui.myia.io/tika, 
timeout: 30s
01:23:30 [WARNING] [Services.CryptoService] Service de chiffrement initialisé sans clé. Le chiffrement est désactivé.
01:23:30 [DEBUG] [argumentation_analysis.agents.core.informal.prompts] Module agents.core.informal.prompts chargé (V8 
- Amélioré, AnalyzeFallacies V1).
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing decorator for function: 
explore_fallacy_hierarchy
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: current_pk_str
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: max_children
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'int'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] annotations=[{'name': 'current_pk_str', 
'is_required': True, 'type_': 'str', 'type_object': <class 'str'>}, {'name': 'max_children', 'default_value': 15, 
'is_required': False, 'type_': 'int', 'type_object': <class 'int'>}]
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: return
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing decorator for function: 
get_fallacy_details
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: fallacy_pk_str
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] annotations=[{'name': 'fallacy_pk_str', 
'is_required': True, 'type_': 'str', 'type_object': <class 'str'>}]
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: return
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing decorator for function: 
find_fallacy_definition
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: fallacy_name
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] annotations=[{'name': 'fallacy_name', 
'is_required': True, 'type_': 'str', 'type_object': <class 'str'>}]
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: return
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing decorator for function: 
list_fallacy_categories
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] annotations=[]
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: return
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing decorator for function: 
list_fallacies_in_category
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: category_name
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] annotations=[{'name': 'category_name', 
'is_required': True, 'type_': 'str', 'type_object': <class 'str'>}]
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: return
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing decorator for function: 
get_fallacy_example
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: fallacy_name
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] annotations=[{'name': 'fallacy_name', 
'is_required': True, 'type_': 'str', 'type_object': <class 'str'>}]
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing param: return
01:23:30 [DEBUG] [semantic_kernel.functions.kernel_function_decorator] Parsing annotation: <class 'str'>
01:23:30 [INFO] [InformalDefinitions] Classe InformalAnalysisPlugin (V12 avec nouvelles fonctions) définie.
01:23:30 [INFO] [InformalDefinitions] Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V15 avec nouvelles fonctions) 
définies.
01:23:30 [DEBUG] [argumentation_analysis.agents.core.informal.informal_definitions] Module 
agents.core.informal.informal_definitions chargé.
[auto_env DEBUG] Début ensure_env. Python: C:\Users\MYIA\miniconda3\envs\projet-is\python.exe, CONDA_DEFAULT_ENV: 
projet-is, silent: False
[auto_env DEBUG] env_man_auto_activate_env a retourné: True
[auto_env DEBUG] Avant vérif critique. Python: C:\Users\MYIA\miniconda3\envs\projet-is\python.exe, CONDA_DEFAULT_ENV: 
projet-is

[DIAGNOSTIC] extract_agent.py: État JVM AVANT _lazy_imports(): started=False
[DIAGNOSTIC] extract_agent.py: État JVM APRÈS _lazy_imports(): started=False
[2025-06-16 01:23:31] [INFO] Activation de l'environnement 'projet-is'...
[2025-06-16 01:23:31] [INFO] Début du bloc d'activation unifié...
[2025-06-16 01:23:31] [INFO] Fichier .env trouvé et chargé depuis : D:\2025-Epita-Intelligence-Symbolique\.env
[2025-06-16 01:23:31] [INFO] [.ENV DISCOVERY] CONDA_PATH déjà présent dans l'environnement.
[2025-06-16 01:23:31] [INFO] [PATH] Ajout au PATH système: C:\tools\miniconda3\Library\bin
[2025-06-16 01:23:31] [INFO] [PATH] Ajout au PATH système: C:\tools\miniconda3\Scripts
[2025-06-16 01:23:31] [INFO] [PATH] Ajout au PATH système: C:\tools\miniconda3\condabin
[2025-06-16 01:23:31] [INFO] [PATH] PATH système mis à jour avec les chemins de CONDA_PATH.
[2025-06-16 01:23:31] [INFO] JAVA_HOME (de .env) converti en chemin absolu: D:\2025-Epita-Intelligence-Symbolique\libs\portable_jdk\jdk-17.0.11+9
[2025-06-16 01:23:31] [INFO] Ajouté D:\2025-Epita-Intelligence-Symbolique\libs\portable_jdk\jdk-17.0.11+9\bin au PATH pour la JVM.
[2025-06-16 01:23:31] [WARNING] NODE_HOME non défini ou invalide. Tentative d'auto-installation...
[2025-06-16 01:23:31] [INFO] Node.js sera installé dans : D:\2025-Epita-Intelligence-Symbolique\libs
[2025-06-16 01:23:31] [DEBUG] setup_tools called with: tools_dir_base_path=D:\2025-Epita-Intelligence-Symbolique\libs, force_reinstall=False, interactive=False, skip_jdk=True, skip_octave=True, skip_node=False
[2025-06-16 01:23:31] [INFO] Skipping JDK setup as per request.
[2025-06-16 01:23:31] [INFO] Skipping Octave setup as per request.
[2025-06-16 01:23:31] [INFO] --- Managing Node.js ---
[2025-06-16 01:23:31] [DEBUG] Initial tool_config for Node.js: {'name': 'Node.js', 'url_windows': 'https://nodejs.org/dist/v20.14.0/node-v20.14.0-win-x64.zip', 'dir_name_pattern': 'node-v20\\.14\\.0-win-x64', 'home_env_var': 'NODE_HOME'}
[2025-06-16 01:23:31] [DEBUG] _find_tool_dir: Found matching dir 'D:\2025-Epita-Intelligence-Symbolique\libs\node-v20.14.0-win-x64' for pattern 'node-v20\.14\.0-win-x64' in 'D:\2025-Epita-Intelligence-Symbolique\libs'.
[2025-06-16 01:23:31] [INFO] Node.js found at: D:\2025-Epita-Intelligence-Symbolique\libs\node-v20.14.0-win-x64
[2025-06-16 01:23:31] [INFO] Using existing Node.js installation.
[2025-06-16 01:23:31] [INFO] Temporary download directory D:\2025-Epita-Intelligence-Symbolique\libs\_temp_downloads can be cleaned up manually for now.
[2025-06-16 01:23:31] [SUCCESS] Node.js auto-installé avec succès dans: D:\2025-Epita-Intelligence-Symbolique\libs\node-v20.14.0-win-x64
[2025-06-16 01:23:31] [DEBUG] Recherche de 'conda.exe' avec shutil.which...
[2025-06-16 01:23:31] [INFO] Exécutable Conda trouvé via shutil.which: C:\tools\miniconda3\Scripts\conda.exe
[2025-06-16 01:23:32] [DEBUG] Chemin trouvé pour 'projet-is': C:\Users\MYIA\miniconda3\envs\projet-is
[2025-06-16 01:23:32] [DEBUG] Environnement conda 'projet-is' trouvé à l'emplacement : C:\Users\MYIA\miniconda3\envs\projet-is
[2025-06-16 01:23:32] [DEBUG] Variable d'environnement définie: PYTHONIOENCODING=utf-8
[2025-06-16 01:23:32] [DEBUG] Variable d'environnement définie: PYTHONPATH=D:\2025-Epita-Intelligence-Symbolique
[2025-06-16 01:23:32] [DEBUG] Variable d'environnement définie: PROJECT_ROOT=D:\2025-Epita-Intelligence-Symbolique
[2025-06-16 01:23:32] [SUCCESS] Environnement 'projet-is' activé (via activate_project_environment)
[2025-06-16 01:23:32] [SUCCESS] Auto-activation de 'projet-is' réussie via le manager central.
[auto_env] Activation de 'projet-is' via EnvironmentManager: SUCCÈS
[2025-06-16 01:23:32] [INFO] [auto_env] Vérification de l'environnement réussie: CONDA_DEFAULT_ENV='projet-is', sys.executable='C:\Users\MYIA\miniconda3\envs\projet-is\python.exe'
01:23:32 [INFO] [root] Logging configuré avec le niveau INFO.
01:23:32 [INFO] [root] Logging configuré avec le niveau INFO.
01:23:32 [INFO] [root] Logging configuré avec le niveau INFO.
01:23:32 [INFO] [root] Logging configuré avec le niveau INFO.
01:23:32 [INFO] [Orchestration.AgentPL.Defs] Classe PropositionalLogicPlugin (V10.1) définie.
01:23:32 [INFO] [Orchestration.AgentPL.Defs] Instructions Système PL_AGENT_INSTRUCTIONS (V10) définies.
01:23:32 [INFO] [Orchestration.AgentPM.Defs] Plugin PM (vide) défini.
01:23:32 [INFO] [Orchestration.AgentPM.Defs] Instructions Système PM_INSTRUCTIONS (V9 - Ajout ExtractAgent) définies.
01:23:32 [ERROR] [root] ❌ Erreur lors de l'orchestration: cannot import name 'run_analysis_conversation' from 'argumentation_analysis.orchestration.analysis_runner' (D:\2025-Epita-Intelligence-Symbolique\argumentation_analysis\orchestration\analysis_runner.py)
Traceback (most recent call last):
  File "D:\2025-Epita-Intelligence-Symbolique\argumentation_analysis\run_orchestration.py", line 111, in run_orchestration
    from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
ImportError: cannot import name 'run_analysis_conversation' from 'argumentation_analysis.orchestration.analysis_runner' (D:\2025-Epita-Intelligence-Symbolique\argumentation_analysis\orchestration\analysis_runner.py)

