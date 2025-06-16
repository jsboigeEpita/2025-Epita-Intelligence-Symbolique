import os
import pytest
import sys
import logging
import threading
import asyncio
import time
import argparse
from project_core.webapp_from_scripts.unified_web_orchestrator import UnifiedWebOrchestrator

# Configuration du logger
logger = logging.getLogger(__name__)

def deep_delete_from_sys_modules(module_name_prefix):
    """Supprime un module et tous ses sous-modules de sys.modules."""
    keys_to_delete = [k for k in sys.modules if k == module_name_prefix or k.startswith(module_name_prefix + '.')]
    if keys_to_delete:
        logger.warning(f"[E2E Conftest] Nettoyage en profondeur des modules pour le préfixe '{module_name_prefix}': {keys_to_delete}")
    for key in keys_to_delete:
        try:
            del sys.modules[key]
        except KeyError:
            pass

@pytest.fixture(scope="session", autouse=True)
def e2e_session_setup(request):
    """
    Fixture de session E2E complète:
    1. Nettoie l'environnement des mocks (NumPy, JPype).
    2. Initialise le vrai JPype et la JVM.
    3. Démarre l'orchestrateur web complet (backend & frontend).
    4. Exécute les tests.
    5. Arrête proprement l'orchestrateur.
    """
    logger.warning("[E2E Conftest] Démarrage de la configuration de session E2E.")

    # 1. & 2. GESTION DE LA JVM DANS LE PROCESSUS DE TEST (DÉSACTIVÉ)
    #
    # NOTE: La tentative d'initialiser une seconde JVM dans le processus de test
    # (alors que le serveur backend en exécute déjà une dans un sous-processus)
    # semble être la cause des crashs "access violation" sur Windows.
    # Les tests E2E ne devraient pas avoir besoin d'accéder directement à des
    # composants Java. Ils doivent traiter le backend comme une boîte noire via HTTP.
    # Nous désactivons donc cette section. L'état "mocké" de jpype dans ce
    # processus n'est pas pertinent pour les tests E2E.
    #
    # logger.warning("[E2E Conftest] Éradication de tout mock (NumPy, JPype).")
    # deep_delete_from_sys_modules("numpy")
    # deep_delete_from_sys_modules("jpype")
    #
    # try:
    #     import jpype
    #     import jpype.imports
    #     logger.warning(f"[E2E Conftest] Vrai JPype (version {jpype.__version__}) importé.")
    #
    #     from argumentation_analysis.core.jvm_setup import initialize_jvm
    #     initialize_jvm(force_restart=False)
    #     if not jpype.isJVMStarted():
    #         pytest.fail("[E2E Conftest] La JVM n'a pas pu démarrer.")
    #
    # except Exception as e:
    #     pytest.fail(f"[E2E Conftest] Échec de l'initialisation de JPype/JVM: {e}")

    # 3. Démarrer l'orchestrateur web
    # Simuler les arguments de ligne de commande nécessaires pour l'orchestrateur
    args = argparse.Namespace(
        config='scripts/webapp/config/webapp_config.yml',
        log_level='DEBUG',
        headless=True,
        visible=False,
        timeout=5, # Timeout de 5 minutes pour les tests
        no_trace=True,
        frontend=True, # Force l'activation du frontend pour les tests E2E
        no_playwright=False, # S'assurer que playwright est actif
        exit_after_start=False
    )
    
    orchestrator = UnifiedWebOrchestrator(args)

    orchestrator.loop = None
    def run_orchestrator():
        orchestrator.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(orchestrator.loop)
        # Démarrer le frontend est nécessaire pour les tests Playwright,
        # on utilise la configuration via l'objet args.
        orchestrator.loop.run_until_complete(orchestrator.start_webapp(headless=args.headless, frontend_enabled=args.frontend))

    orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
    orchestrator_thread.start()
    
    # Attendre que les serveurs soient prêts
    logger.info("[E2E Conftest] En attente du démarrage des serveurs...")
    start_time = time.time()
    # Utilise la méthode is_ready() de l'orchestrateur qui a une logique interne
    # de health check, mais ajoutons un timeout externe pour la fixture.
    start_time = time.time()
    timeout_fixture = 180  # secondes
    
    while not orchestrator.is_ready():
        if time.time() - start_time > timeout_fixture:
            # En cas de timeout, on tente d'arrêter proprement avant de faire échouer le test.
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Ne pas appeler run_until_complete sur une boucle qui tourne déjà
                    future = asyncio.run_coroutine_threadsafe(orchestrator.stop_webapp(), loop)
                    future.result(timeout=20) # Attendre que l'arrêt se termine
                else:
                    asyncio.run(orchestrator.stop_webapp())
            except Exception as e:
                logger.error(f"[E2E Conftest] Échec de l'arrêt de l'orchestrateur après timeout: {e}")
            
            pytest.fail(f"[E2E Conftest] Timeout de {timeout_fixture}s dépassé: Les serveurs web ne sont pas prêts.")
        
        time.sleep(1)
    
    logger.info("[E2E Conftest] Orchestrateur Web prêt. Exécution des tests.")
    
    def finalizer():
        logger.warning("[E2E Conftest] Finalizer: Arrêt de l'orchestrateur Web.")
        
        # Pour arrêter proprement, on doit appeler la coroutine `stop_webapp`
        # dans une boucle d'événements asyncio.
        if orchestrator.loop and not orchestrator.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(orchestrator.stop_webapp(), orchestrator.loop)
            try:
                future.result(timeout=30)
            except Exception as e:
                 logger.error(f"[E2E Conftest] Échec de l'arrêt de l'orchestrateur via run_coroutine_threadsafe: {e}")
        else:
            logger.warning("[E2E Conftest] Impossible d'arrêter l'orchestrateur, la boucle d'événements n'est pas disponible.")

        # S'assurer que le thread se termine
        if orchestrator_thread.is_alive():
            orchestrator_thread.join(timeout=20)
        
        logger.warning("[E2E Conftest] Orchestrateur Web arrêté.")

    request.addfinalizer(finalizer)

    yield orchestrator