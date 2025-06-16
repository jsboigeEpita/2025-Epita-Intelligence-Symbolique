conda.exe : 01:30:04 [INFO] [App.UI.CacheUtils] Utilitaires de cache UI définis.
Au caractère C:\Tools\miniconda3\shell\condabin\Conda.psm1:153 : 17
+ ...             & $Env:CONDA_EXE $Env:_CE_M $Env:_CE_CONDA $Command @Othe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (01:30:04 [INFO]...che UI définis.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
01:30:05 [INFO] [App.UI.FetchUtils] Utilitaires de fetch UI définis.
01:30:05 [INFO] [App.UI.VerificationUtils] Utilitaires de vérification UI définis.
01:30:05 [INFO] [App.UI.Utils] Module principal des utilitaires UI (utils.py) initialisé et sous-modules importés.
01:30:05 [INFO] [Services.CacheService] Répertoire de cache initialisé: 
D:\2025-Epita-Intelligence-Symbolique\_temp\text_cache
01:30:05 [INFO] [Services.FetchService] FetchService initialisé avec Tika URL: https://tika.open-webui.myia.io/tika, 
timeout: 30s
01:30:05 [WARNING] [Services.CryptoService] Service de chiffrement initialisé sans clé. Le chiffrement est désactivé.
01:30:05 [INFO] [InformalDefinitions] Classe InformalAnalysisPlugin (V12 avec nouvelles fonctions) définie.
01:30:05 [INFO] [InformalDefinitions] Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V15 avec nouvelles fonctions) 
définies.
[auto_env DEBUG] Début ensure_env. Python: C:\Users\MYIA\miniconda3\envs\projet-is\python.exe, CONDA_DEFAULT_ENV: 
projet-is, silent: False
[auto_env DEBUG] env_man_auto_activate_env a retourné: True
[auto_env DEBUG] Avant vérif critique. Python: C:\Users\MYIA\miniconda3\envs\projet-is\python.exe, CONDA_DEFAULT_ENV: 
projet-is
Traceback (most recent call last):
  File 
"D:\2025-Epita-Intelligence-Symbolique\argumentation_analysis\agents\orchestration\einstein_sherlock_watson_demo.py", 
line 65, in initialize_agents
    self.sherlock_agent = SherlockEnqueteAgent(
TypeError: Can't instantiate abstract class SherlockEnqueteAgent with abstract method invoke_single

[DIAGNOSTIC] extract_agent.py: État JVM AVANT _lazy_imports(): started=False
[DIAGNOSTIC] extract_agent.py: État JVM APRÈS _lazy_imports(): started=False
[2025-06-16 01:30:05] [INFO] Activation de l'environnement 'projet-is'...
[2025-06-16 01:30:05] [INFO] Début du bloc d'activation unifié...
[2025-06-16 01:30:05] [INFO] Fichier .env trouvé et chargé depuis : D:\2025-Epita-Intelligence-Symbolique\.env
[2025-06-16 01:30:05] [INFO] [.ENV DISCOVERY] CONDA_PATH déjà présent dans l'environnement.
[2025-06-16 01:30:05] [INFO] [PATH] Ajout au PATH système: C:\tools\miniconda3\Library\bin
[2025-06-16 01:30:05] [INFO] [PATH] Ajout au PATH système: C:\tools\miniconda3\Scripts
[2025-06-16 01:30:05] [INFO] [PATH] Ajout au PATH système: C:\tools\miniconda3\condabin
[2025-06-16 01:30:05] [INFO] [PATH] PATH système mis à jour avec les chemins de CONDA_PATH.
[2025-06-16 01:30:05] [INFO] JAVA_HOME (de .env) converti en chemin absolu: D:\2025-Epita-Intelligence-Symbolique\libs\portable_jdk\jdk-17.0.11+9
[2025-06-16 01:30:05] [INFO] Ajouté D:\2025-Epita-Intelligence-Symbolique\libs\portable_jdk\jdk-17.0.11+9\bin au PATH pour la JVM.
[2025-06-16 01:30:05] [WARNING] NODE_HOME non défini ou invalide. Tentative d'auto-installation...
[2025-06-16 01:30:05] [INFO] Node.js sera installé dans : D:\2025-Epita-Intelligence-Symbolique\libs
[2025-06-16 01:30:05] [DEBUG] setup_tools called with: tools_dir_base_path=D:\2025-Epita-Intelligence-Symbolique\libs, force_reinstall=False, interactive=False, skip_jdk=True, skip_octave=True, skip_node=False
[2025-06-16 01:30:05] [INFO] Skipping JDK setup as per request.
[2025-06-16 01:30:05] [INFO] Skipping Octave setup as per request.
[2025-06-16 01:30:05] [INFO] --- Managing Node.js ---
[2025-06-16 01:30:05] [DEBUG] Initial tool_config for Node.js: {'name': 'Node.js', 'url_windows': 'https://nodejs.org/dist/v20.14.0/node-v20.14.0-win-x64.zip', 'dir_name_pattern': 'node-v20\\.14\\.0-win-x64', 'home_env_var': 'NODE_HOME'}
[2025-06-16 01:30:05] [DEBUG] _find_tool_dir: Found matching dir 'D:\2025-Epita-Intelligence-Symbolique\libs\node-v20.14.0-win-x64' for pattern 'node-v20\.14\.0-win-x64' in 'D:\2025-Epita-Intelligence-Symbolique\libs'.
[2025-06-16 01:30:05] [INFO] Node.js found at: D:\2025-Epita-Intelligence-Symbolique\libs\node-v20.14.0-win-x64
[2025-06-16 01:30:05] [INFO] Using existing Node.js installation.
[2025-06-16 01:30:05] [INFO] Temporary download directory D:\2025-Epita-Intelligence-Symbolique\libs\_temp_downloads can be cleaned up manually for now.
[2025-06-16 01:30:05] [SUCCESS] Node.js auto-installé avec succès dans: D:\2025-Epita-Intelligence-Symbolique\libs\node-v20.14.0-win-x64
[2025-06-16 01:30:05] [DEBUG] Recherche de 'conda.exe' avec shutil.which...
[2025-06-16 01:30:05] [INFO] Exécutable Conda trouvé via shutil.which: C:\tools\miniconda3\Scripts\conda.exe
[2025-06-16 01:30:06] [DEBUG] Chemin trouvé pour 'projet-is': C:\Users\MYIA\miniconda3\envs\projet-is
[2025-06-16 01:30:06] [DEBUG] Environnement conda 'projet-is' trouvé à l'emplacement : C:\Users\MYIA\miniconda3\envs\projet-is
[2025-06-16 01:30:06] [DEBUG] Variable d'environnement définie: PYTHONIOENCODING=utf-8
[2025-06-16 01:30:06] [DEBUG] Variable d'environnement définie: PYTHONPATH=D:\2025-Epita-Intelligence-Symbolique
[2025-06-16 01:30:06] [DEBUG] Variable d'environnement définie: PROJECT_ROOT=D:\2025-Epita-Intelligence-Symbolique
[2025-06-16 01:30:06] [SUCCESS] Environnement 'projet-is' activé (via activate_project_environment)
[2025-06-16 01:30:06] [SUCCESS] Auto-activation de 'projet-is' réussie via le manager central.
[auto_env] Activation de 'projet-is' via EnvironmentManager: SUCCÈS
[2025-06-16 01:30:06] [INFO] [auto_env] Vérification de l'environnement réussie: CONDA_DEFAULT_ENV='projet-is', sys.executable='C:\Users\MYIA\miniconda3\envs\projet-is\python.exe'
01:30:06 [INFO] [root] Logging configuré avec le niveau INFO.
01:30:06 [INFO] [root] Logging configuré avec le niveau INFO.
01:30:06 [INFO] [root] Logging configuré avec le niveau INFO.
01:30:06 [INFO] [root] Logging configuré avec le niveau INFO.
01:30:06 [INFO] [Orchestration.AgentPL.Defs] Classe PropositionalLogicPlugin (V10.1) définie.
01:30:06 [INFO] [Orchestration.AgentPL.Defs] Instructions Système PL_AGENT_INSTRUCTIONS (V10) définies.
01:30:07 [INFO] [Orchestration.LLM] <<<<< MODULE llm_service.py LOADED >>>>>
01:30:07 [ERROR] [__main__] Erreur lors de l'initialisation des agents: Can't instantiate abstract class SherlockEnqueteAgent with abstract method invoke_single
❌ Échec de la démonstration Einstein

