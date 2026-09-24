import json

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration pytest globale pour l'ensemble des tests du projet.
"""

import pytest
import logging
import os
import sys
import asyncio
from pathlib import Path
import shutil
from unittest.mock import patch, MagicMock

# #2472: capture the environment pytest was started with, before anything loads
# a .env. A value set on the command line, even "", then wins over the root .env
# that ensure_env() loads in pytest_configure.
import project_core.managers.environment_manager  # noqa: F401

from tests._e2e_session_decision import _argv_decides_e2e_session
from tests._jvm_session_flag import (
    JVM_SESSION_DISABLED_ENV as _JVM_SESSION_DISABLED_ENV,
    export_flag_from_config as _export_jvm_flag_from_config,
    jvm_session_disabled as _jvm_session_disabled,
    propagate_argv_to_env as _propagate_jvm_flag_argv_to_env,
    put_back as _put_back_jvm_flag,
)
from tests.jvm_skip_storm_signal import COUNTER as _skip_storm_counter
from tests.jvm_skip_storm_signal import storm_verdict as _storm_verdict
from tests.jvm_skip_storm_signal import ventilate as _storm_ventilate
import nest_asyncio

# Apply nest_asyncio early at module level to allow nested event loops
nest_asyncio.apply()

# Patch backports.asyncio.runner.Runner.run for nest_asyncio compatibility.
# nest_asyncio patches asyncio.run() and loop.run_until_complete(), but NOT
# backports.asyncio.runner.Runner.run() which pytest_asyncio uses internally.
# Without this patch, pytest_asyncio fixtures fail with:
#   "RuntimeError: Runner.run() cannot be called from a running event loop"
# when Playwright or other plugins maintain a running event loop.
try:
    from backports.asyncio.runner import runner as _br
    import asyncio.events as _aevt

    _orig_runner_run = _br.Runner.run

    def _patched_runner_run(self, coro, *, context=None):
        # Only suppress _get_running_loop for the initial guard check inside
        # Runner.run (which raises "cannot be called from a running event loop").
        # We must NOT keep _get_running_loop patched during actual coroutine
        # execution, because asyncio.Event/Lock/Condition rely on it to bind
        # to the running loop (Python 3.10+ _LoopBoundMixin).
        _saved = _aevt._get_running_loop
        _aevt._get_running_loop = lambda: None
        try:
            self._lazy_init()
        finally:
            _aevt._get_running_loop = _saved

        # Now run the coroutine with the real _get_running_loop restored.
        # We replicate the core of Runner.run but skip the guard check.
        import asyncio
        import contextvars
        import functools
        import signal
        import threading
        from asyncio import coroutines, exceptions

        if context is None:
            context = self._context

        task = self._loop.create_task(coro)

        if (
            threading.current_thread() is threading.main_thread()
            and signal.getsignal(signal.SIGINT) is signal.default_int_handler
        ):
            sigint_handler = functools.partial(self._on_sigint, main_task=task)
            try:
                signal.signal(signal.SIGINT, sigint_handler)
            except ValueError:
                sigint_handler = None
        else:
            sigint_handler = None

        self._interrupt_count = 0
        try:
            return self._loop.run_until_complete(task)
        except exceptions.CancelledError:
            if self._interrupt_count > 0:
                uncancel = getattr(task, "uncancel", None)
                if uncancel is not None and uncancel() == 0:
                    raise KeyboardInterrupt()
            raise
        finally:
            if (
                sigint_handler is not None
                and signal.getsignal(signal.SIGINT) is sigint_handler
            ):
                signal.signal(signal.SIGINT, signal.default_int_handler)

    _br.Runner.run = _patched_runner_run
except (ImportError, AttributeError):
    pass

# --- Mocking global pour les tests E2E ---
# Si --disable-jvm-session est présent, on mocke jpype AVANT toute autre importation.
# #2402 : la décision est exportée une fois dans l'environnement (cf.
# _jvm_session_flag) — le propagateur argv ne couvre que le bootstrap
# pré-configure du contrôleur ; les workers lisent l'env var héritée.
_propagate_jvm_flag_argv_to_env()
_disable_jvm_early_check = _jvm_session_disabled()
if _disable_jvm_early_check:
    print("[INFO] Early check: --disable-jvm-session detected. Mocking jpype globally.")
    _mock_jpype = MagicMock()
    _mock_jpype.__version__ = "1.6.0-mock"
    sys.modules["jpype"] = _mock_jpype
    sys.modules["jpype.imports"] = MagicMock()

# Désactive la vérification de l'environnement Conda pour les tests E2E
os.environ["E2E_TESTING_MODE"] = "1"

# --- Importations préventives pour éviter les conflits de bas niveau ---
# Il est crucial d'importer les bibliothèques lourdes comme torch et transformers
# AVANT que jpype ne soit initialisé pour éviter des crashs de type "access violation".
# Ces imports sont effectués au niveau du module pour garantir qu'ils sont chargés
# avant même que pytest ne commence à traiter les fixtures.
try:
    import torch
    import transformers
    import openai
    import semantic_kernel
except (ImportError, OSError, RuntimeError) as e:
    # Utilise print car le logger n'est pas encore configuré à ce stade.
    print(
        f"[AVERTISSEMENT CONTEST] L'importation préventive d'une bibliothèque a échoué: {e}",
        file=sys.stderr,
    )

# --- Import jpype APRÈS torch pour éviter conflit DLL Windows ---
# CRITIQUE : jpype doit être importé APRÈS torch/transformers pour éviter
# "OSError: [WinError 182] torch\lib\fbgemm.dll" sur Windows
import jpype

# Ajouter le répertoire racine et les sous-répertoires pertinents au PYTHONPATH
project_root = Path(__file__).parent.parent
additional_paths = [
    str(project_root),
    str(project_root / "scripts"),
    str(project_root / "examples" / "scripts_demonstration"),
    str(project_root / "services"),
]
for path in additional_paths:
    if path not in sys.path:
        sys.path.insert(0, path)

# Importations nécessaires pour les fixtures ci-dessous


logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Ajoute des options de ligne de commande personnalisées à pytest."""
    parser.addoption(
        "--allow-dotenv",
        action="store_true",
        default=False,
        help=(
            "Charge aussi .env.test (s'il existe) par-dessus le .env racine, que "
            "pytest_configure charge sans ce drapeau. Une valeur posée par "
            "l'appelant, même vide, l'emporte sur les deux (#2472)."
        ),
    )
    parser.addoption(
        "--disable-e2e-servers-fixture",
        action="store_true",
        default=False,
        help="Désactive la fixture qui gère les serveurs E2E.",
    )
    parser.addoption(
        "--disable-jvm-session",
        action="store_true",
        default=False,
        help="Désactive complètement la fixture de session JVM.",
    )
    parser.addoption(
        "--frontend-url",
        action="store",
        default="http://localhost:8085",
        help="URL pour le serveur frontend E2E.",
    )
    parser.addoption(
        "--backend-url",
        action="store",
        default="http://localhost:8095",
        help="URL pour le serveur backend E2E.",
    )


def pytest_configure(config):
    """
    Hook de configuration précoce de pytest.
    """
    # #2402 : un seul lecteur du drapeau --disable-jvm-session — la décision
    # est prise ici (config analysé, donc addopts compris) et exportée aux
    # workers via l'environnement. Doit tourner AVANT le spawn xdist.
    _export_jvm_flag_from_config(config)

    # ========================== VÉRIFICATION CRITIQUE DE L'ENVIRONNEMENT ==========================
    # Le bloc suivant est essentiel pour garantir que les tests s'exécutent dans le bon environnement Conda.
    # NE PAS COMMENTER OU DÉSACTIVER, sauf en cas de maintenance délibérée de l'infrastructure de test.
    try:
        from argumentation_analysis.core.environment import ensure_env

        ensure_env()
    except RuntimeError as e:
        pytest.exit(
            f"\n\n[FATAL] ERREUR DE CONFIGURATION DE L'ENVIRONNEMENT:\n{e}",
            returncode=1,
        )
    # ===============================================================================================

    # Désactive dynamiquement le plugin opentelemetry pour éviter les conflits
    # avec jpype, qui peuvent causer un crash "access violation" sur Windows.
    if "opentelemetry" in config.pluginmanager.list_name_plugin():
        plugin = config.pluginmanager.get_plugin("opentelemetry")
        config.pluginmanager.unregister(plugin)
        print(
            "Plugin opentelemetry désenregistré pour éviter le crash de la JVM.",
            file=sys.stderr,
        )

    # The root .env is loaded above by ensure_env(). --allow-dotenv layers
    # .env.test over it; a value the caller set wins over both (#2472).
    if config.getoption("--allow-dotenv"):
        from project_core.managers import environment_manager as _env_manager

        repo_root = _env_manager._find_repo_root()
        dotenv_test_path = repo_root / ".env.test" if repo_root else None
        if dotenv_test_path is not None and dotenv_test_path.exists():
            print(f"\n[INFO] --allow-dotenv: loading {dotenv_test_path}.")
            _env_manager.load_env_file(dotenv_test_path)
        else:
            print("\n[INFO] --allow-dotenv: no .env.test to layer.")

    # --- Désactivation d'OpenTelemetry pour les tests ---
    # Pour éviter les erreurs de connexion pendant les tests, nous désactivons
    # explicitement les exportateurs OTLP, sauf si demandé autrement.
    print("\\n[INFO] Disabling OpenTelemetry exporters for tests by default.")
    os.environ["OTEL_TRACES_EXPORTER"] = "none"
    os.environ["OTEL_METRICS_EXPORTER"] = "none"
    os.environ["OTEL_LOGS_EXPORTER"] = "none"

    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "api: marks tests related to the API")
    config.addinivalue_line(
        "markers", "timeout: marks tests with a timeout guard (seconds)"
    )
    config.addinivalue_line(
        "markers", "real_llm: marks tests that require a real LLM service"
    )
    config.addinivalue_line(
        "markers", "real_jpype: marks tests that require a real JPype/JVM environment"
    )
    config.addinivalue_line(
        "markers",
        "no_jvm_session: marks tests that should not start the shared JVM session",
    )
    config.addinivalue_line(
        "markers",
        "jvm_test: (deprecated, use jpype) marks tests that require the JVM to be started.",
    )

    # LLM egress counter (#1787) — observation-only instrument. Counts outgoing
    # httpx requests to LLM hosts for the whole session (SK kernel path, direct
    # AsyncOpenAI path, embeddings: all transit through httpx). Installed AFTER
    # env loading above so endpoint env vars are visible for host resolution.
    # Never blocks; report lands in the terminal summary + llm_egress_report.json
    # next to the junitxml. Non-vacuity control: tests/unit/test_llm_egress_counter.py.
    from tests.llm_egress_counter import LLMEgressPlugin, activate

    _llm_egress = activate()
    config.pluginmanager.register(
        LLMEgressPlugin(_llm_egress), name="llm_egress_counter"
    )


class _NullCache:
    """#1820 : cache de secours quand ``-p no:cacheprovider`` est passé —
    ``config.cache`` n'existe pas et chaque accès levait en INTERNALERROR avant
    toute collecte. ``get``/``set`` round-trippent dans un dict de classe : le
    transport intra-session (sessionstart écrit ``jvm_started``, la fixture
    ``jvm_session`` le lit) reste fonctionnel — un set-noop aurait fait sauter
    à tort les tests JVM d'une session où la JVM VIT. Portée = le process
    pytest : chaque invocation repart vierge (sémantique cache froid), rien
    ne persiste entre runs."""

    _store: dict = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value


def _cache(config):
    """#1820 : accès unique au cache pytest pour les 9 sites de conftest."""
    return getattr(config, "cache", None) or _NullCache()


def pytest_collection_finish(session):
    """
    Hook exécuté après la collecte des tests.
    Détecte si des tests E2E sont présents et stocke le résultat dans le cache.
    """
    is_e2e_session = any(
        item.get_closest_marker("e2e") is not None for item in session.items
    )
    _cache(session.config).set("is_e2e_session", is_e2e_session)
    if is_e2e_session:
        logger.warning(
            "Session de test E2E détectée. L'initialisation globale de la JVM sera sautée."
        )


@pytest.fixture
def mock_chat_completion_service():
    """Mock LLM service compatible Pydantic ChatCompletionAgent.

    Utilise MagicMock avec spec=ChatCompletionClientBase pour passer
    validation Pydantic lors de l'initialisation de BaseAgent héritant
    ChatCompletionAgent (correction Mission D3.2 Phase B).

    Returns:
        MagicMock: Service mock avec spec ChatCompletionClientBase
    """
    from semantic_kernel.connectors.ai.chat_completion_client_base import (
        ChatCompletionClientBase,
    )
    from semantic_kernel.contents import ChatMessageContent
    from unittest.mock import MagicMock, AsyncMock

    # Mock avec spec pour validation Pydantic
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.service_id = "test_llm_service"
    mock_service.ai_model_id = "test-model"

    # Mock méthode get_chat_message_contents (async)
    async def mock_get_chat_message_contents(*args, **kwargs):
        return [ChatMessageContent(role="assistant", content="Mock response")]

    mock_service.get_chat_message_contents = AsyncMock(
        side_effect=mock_get_chat_message_contents
    )

    return mock_service


@pytest.fixture
def mock_kernel_with_llm(mock_chat_completion_service):
    """Kernel avec service LLM mock Pydantic-compatible pré-configuré.

    Utilise mock_chat_completion_service pour garantir compatibilité
    avec BaseAgent héritant ChatCompletionAgent (Mission D3.2 Phase B).

    Args:
        mock_chat_completion_service: Fixture service mock Pydantic-compatible

    Returns:
        Kernel: Instance Kernel avec service LLM mock ajouté
    """
    from semantic_kernel import Kernel

    kernel = Kernel()
    kernel.add_service(mock_chat_completion_service)
    return kernel


def _run_torch_dll_probe(session):
    """#1651 — sonde de chargement DLL torch, en sous-processus isolé.

    Le skip-storm 0xc0000138 (STATUS_ORDINAL_NOT_FOUND) meurt avant tout log
    exploitable : PATH effectif et DLL fautive partent avec la VM. La sonde
    rejoue la séquence de chargement de torch de façon attrapable et écrit un
    log flushé ligne à ligne. Sous-processus : un pre-flight dans CE processus
    chargerait les DLL en premier et masquerait le défaut mesuré.

    Instrument pur — un échec de sonde ne doit jamais casser la session (le
    signal réel reste l'import torch + le garde #1385). Kill-switch local :
    TORCH_DLL_PROBE=0.
    """
    if os.environ.get("TORCH_DLL_PROBE") == "0":
        return
    try:
        import subprocess

        probe = (
            Path(__file__).resolve().parent.parent
            / "scripts"
            / "diagnostics"
            / "probe_torch_dll_load.py"
        )
        if not probe.is_file():
            print(f"[torch-dll-probe] script absent: {probe}", file=sys.stderr)
            return
        result = subprocess.run(
            [sys.executable, str(probe), "--log", "torch_dll_probe.log"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(probe.parent.parent.parent),
        )
        tail = (result.stdout or "").strip().splitlines()[-3:]
        for line in tail:
            print(f"[torch-dll-probe] {line}")
    except Exception as exc:  # noqa: BLE001 — instrument, jamais bloquant
        print(f"[torch-dll-probe] sonde non exécutée: {exc}", file=sys.stderr)


def pytest_sessionstart(session):
    """
    Hook exécuté au tout début de la session de test, avant la collecte.
    C'est l'endroit le plus sûr pour initialiser la JVM afin d'éviter les conflits
    avec les bibliothèques natives chargées par les plugins pytest.
    """
    _run_torch_dll_probe(session)
    logger.info("=" * 80)
    logger.info("pytest_sessionstart: Vérification pour l'initialisation de la JVM...")
    logger.info("=" * 80)

    # Skip JVM init en mode --collect-only (évite conflit torch/JVM)
    if session.config.option.collectonly:
        logger.info(
            "Mode collection uniquement : JVM non initialisée (évite conflit torch/DLL)"
        )
        _cache(session.config).set("jvm_started", False)
        return

    if session.config.getoption("--disable-jvm-session"):
        logger.warning("Initialisation de la JVM sautée via --disable-jvm-session.")
        _cache(session.config).set("jvm_started", False)
        return

    # #1820 : la décision vient de l'ARGV (chemins + -m), toujours connus ici.
    # L'ancien `_cache(...).get("is_e2e_session", False)` lisait un créneau
    # écrit PLUS TARD par pytest_collection_finish — le lecteur tourne avant
    # l'écrivain, donc sur cache froid il lisait le défaut False (JVM démarrée
    # même pour une session e2e : le crash torch/JVM que D3.1.1 évite) et sur
    # cache chaud la valeur d'un RUN PRÉCÉDENT. Le classifieur réplique en argv
    # ce que la collecte dirait. Le writer (collection_finish) et le consommateur
    # (jvm_session) restent inchangés : la fixture lit toujours la vérité
    # post-collecte.
    is_e2e_session = _argv_decides_e2e_session(session.config)

    if is_e2e_session:
        logger.warning(
            "Décision confirmée: L'initialisation globale de la JVM est sautée pour la session E2E."
        )
        _cache(session.config).set("jvm_started", False)
        return

    # #1641 (B): pytest captures logs per-test and only releases them on a test
    # FAILURE. pytest_sessionstart runs before any test, so on a green or skip-
    # heavy run its logs (and jvm_setup's logger.critical failure causes) are
    # swallowed — the diagnostic is lost EXACTLY when the CI guard #1385 trips
    # on a mass-skip storm. Route the JVM-init diagnostics to stdout for the
    # duration of the init attempt, bypassing pytest's capture, so the next
    # storm arrives with its cause in the CI log. Scoped to the call (handler
    # removed in finally); attached to the ROOT logger so jvm_setup's critical
    # lines (different logger) propagate through.
    _diag_handler = logging.StreamHandler(sys.stdout)
    _diag_handler.setLevel(logging.INFO)
    _diag_handler.set_name("jvm_sessionstart_diag_1641")
    logging.getLogger().addHandler(_diag_handler)
    try:
        from argumentation_analysis.core.jvm_setup import initialize_jvm

        # #1641: honor the bool return. initialize_jvm signals a DECIDED failure
        # (no Java / no JARs / post-shutdown re-init) by RETURNING False, not by
        # raising — 5 reachable return-False paths (jvm_setup.py l.773/781/791/…).
        # Discarding the return and forcing jvm_started=True recorded that decided
        # failure as "started": the l.513 guard then never fired, the skip fell
        # through to the l.522 jpype double-check, whose message ("JVM pas
        # réellement démarrée") reads as a transient native crash — so the CI
        # guard #1385 says "re-run" where the real fix is a config correction. A
        # decided failure rendered as an alea (#1019 family, same shape as #1634).
        # Propagating the return makes the l.513 guard fire and the skip carry the
        # honest "l'initialisation a échoué" message. The except below still covers
        # a genuine raise; the l.522 double-check still covers a real post-start
        # crash — three distinct causes, three distinct messages, all kept.
        _jvm_ok = initialize_jvm(session_fixture_owns_jvm=True)
        _cache(session.config).set("jvm_started", bool(_jvm_ok))
        if _jvm_ok:
            logger.info("JVM initialisée avec succès depuis pytest_sessionstart.")
        else:
            logger.error(
                "initialize_jvm() a retourné False — échec d'initialisation DÉCIDÉ "
                "(voir les logger.critical ci-dessus : pas de Java / JARs manquants / "
                "ré-init après arrêt). Le garde jvm_session sautera les tests JVM avec "
                "le message d'échec d'init, pas le message de crash transitoire (#1641)."
            )
    except Exception as e:
        logger.error(
            f"ÉCHEC CRITIQUE de l'initialisation de la JVM dans pytest_sessionstart: {e}"
        )
        _cache(session.config).set("jvm_started", False)
        # On ne lance pas pytest.exit ici pour laisser les tests non-JVM s'exécuter
        # Mais on pourrait le faire si la JVM est absolument critique pour toute la suite.
    finally:
        logging.getLogger().removeHandler(_diag_handler)


def pytest_runtest_logreport(report):
    """#2021: feed the local skip-storm signal (see tests/jvm_skip_storm_signal.py)."""
    _skip_storm_counter.add(report)


_JVM_FLAG_AT_SETUP = pytest.StashKey[object]()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item):
    """#2530: note the JVM flag before the test's fixtures run."""
    item.stash[_JVM_FLAG_AT_SETUP] = os.environ.get(_JVM_SESSION_DISABLED_ENV)
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    """#2530: after the fixtures are torn down, the JVM flag must be back to
    its value at setup. A test that changed it errors here, by name, and the
    value is put back (``tests/_jvm_session_flag.put_back``)."""
    if _JVM_FLAG_AT_SETUP not in item.stash:
        return (yield)
    try:
        result = yield
    finally:
        moved = _put_back_jvm_flag(item.stash[_JVM_FLAG_AT_SETUP])
    if moved is not None:
        pytest.fail(moved, pytrace=False)
    return result


def _skip_storm_signal(session, exitstatus):
    """#2021 — local fail-loud twin of the CI skip-storm guard (ci.yml #1385/#1873).

    A failed JVM init in pytest_sessionstart makes the autouse jvm_session
    fixture skip EVERY test at setup; the session exits 0 in under a second
    having measured nothing. In CI the pwsh guard catches it; locally it
    rendered as a plausible-looking ``N skipped ... in 0.7s`` — three agents
    hit the shape in one round, one as a born-red that never ran (#2021).

    Exempt by design: sessions where JVM-less is a CHOICE (--disable-jvm-session,
    E2E classification) — a JVM-less environment must still be able to run
    the non-JVM suite. The defect is that a vacuous run is SILENT, not that
    it skips. Never make the conftest fail instead of skip (#2021 anti-pendulum).
    """
    if exitstatus != 0:
        return  # already red — there is no green mask to lift
    config = session.config
    if config.option.collectonly:
        return
    if config.getoption("--disable-jvm-session"):
        return
    if _cache(config).get("is_e2e_session", False) or _argv_decides_e2e_session(config):
        return
    jvm_reasons = _skip_storm_counter.jvm_signature_reasons()
    # #2490: the count the session decided on. The xdist controller collects
    # nothing itself, so ``session.items`` stays empty there, and xdist
    # publishes the workers' count in ``session.testscollected``. Serially
    # the two are equal.
    shout, message = _storm_verdict(session.testscollected, len(jvm_reasons))
    if not shout:
        return
    # print, not logger: sessionfinish runs after per-test capture is gone,
    # and the line must survive in the terminal the worker actually reads.
    print("=" * 60)
    print(message)
    print(_storm_ventilate(jvm_reasons))
    print(
        "  The storm is a failed measurement, not a broken suite: re-run the\n"
        "  non-JVM work with --disable-jvm-session (jpype mocked), and treat any\n"
        "  born-red or suite result from THIS session as not executed."
    )
    print("=" * 60)
    pytest.exit(
        "skip-storm signal tripped (#2021) — see the FAIL-LOUD block above",
        returncode=1,
    )


def pytest_sessionfinish(session, exitstatus):
    """
    Hook exécuté à la toute fin de la session de test.
    """
    # L'arrêt de la JVM est instable, on se conforme au commentaire existant.
    logger.info("=" * 80)
    logger.info(
        "pytest_sessionfinish: L'arrêt de la JVM est désactivé pour plus de stabilité."
    )
    logger.info("=" * 80)
    _skip_storm_signal(session, exitstatus)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Fixture de session pour configurer l'environnement de test global.
    Définit une variable d'environnement pour signaler que les tests sont en cours.
    """
    os.environ["PYTEST_RUNNING"] = "1"
    # --- FORCER LE SOLVEUR 'TWEETY' ---
    # Pour éviter le crash 'access violation' causé par le conflit entre la JVM
    # et la DLL native de Prover9, nous forçons l'utilisation du solveur 'tweety'
    # pour toute la session de test.
    os.environ["ARG_ANALYSIS_SOLVER"] = "tweety"
    logger.info("Variable d'environnement 'PYTEST_RUNNING' définie à '1'.")
    logger.info(
        "Variable d'environnement 'ARG_ANALYSIS_SOLVER' forcée à 'tweety' pour éviter les conflits natifs."
    )

    yield

    del os.environ["PYTEST_RUNNING"]
    # Pas besoin de supprimer ARG_ANALYSIS_SOLVER car l'environnement est propre à cette session de test
    logger.info("Variable d'environnement 'PYTEST_RUNNING' supprimée.")


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio():
    """
    Ensures nest_asyncio is applied. The actual apply() call is done at module
    level (top of this file) for earliest possible initialization. This fixture
    exists for backward compatibility and logging.
    """
    logger.info("nest_asyncio.apply() was called at module level (early init).")
    yield


@pytest.fixture(scope="session", autouse=True)
def jvm_session(request):
    """
    Fixture de session qui sert maintenant de "garde" pour les tests nécessitant la JVM.
    L'initialisation réelle a été déplacée vers `pytest_sessionstart` pour une exécution
    plus précoce et plus sûre. Cette fixture vérifie si l'initialisation a réussi.
    """
    jvm_started = _cache(request.config).get("jvm_started", False)
    is_e2e_session = _cache(request.config).get("is_e2e_session", False)

    is_no_jvm_test = "no_jvm_session" in request.node.keywords
    is_jvm_disabled_globally = request.config.getoption("--disable-jvm-session")

    # Si c'est une session E2E, on ne fait rien et on laisse le test s'exécuter
    # même si la JVM n'est pas démarrée. Les tests E2E ne doivent pas dépendre de la JVM.
    if is_e2e_session:
        yield
        return

    # Si la JVM n'est pas nécessaire ou désactivée, on ne fait rien.
    if is_no_jvm_test or is_jvm_disabled_globally:
        yield
        return

    # Si le test nécessite la JVM mais qu'elle n'a pas démarré, on le saute.
    if not jvm_started:
        pytest.skip(
            "Saut du test car l'initialisation de la JVM a échoué dans pytest_sessionstart."
        )

    # Double-check: verify JVM is actually functional (cache may say True
    # even when JVM crashed with a Windows access violation during startup)
    import jpype

    if not jpype.isJVMStarted():
        pytest.skip(
            "Saut du test car la JVM n'est pas réellement démarrée (jpype.isJVMStarted() = False)."
        )

    # Health check: try a simple Java operation to confirm JVM is not corrupted
    try:
        _str_class = jpype.JClass("java.lang.String")
        _test = _str_class("jvm_health_check")
        assert str(_test) == "jvm_health_check"
    except Exception as exc:
        # #2530: the reason names the exception, or a broken JVM leaves no
        # trace of why. Both classifiers of this reason (the local signal and
        # the ci.yml guard) read its fixed start, so the storm counts do not
        # move; the contract tests harvest that start from the f-string.
        pytest.skip(
            "Saut du test car la JVM est démarrée mais non fonctionnelle "
            f"(JClass health check échoué) : {type(exc).__name__}: {str(exc)[:500]}"
        )

    # La JVM est prête — yield le module jpype pour que les fixtures
    # puissent utiliser jvm_session.JClass(), etc.
    yield jpype


# La fixture jvm_fixture est supprimée car elle est la source des conflits.
# La gestion de la JVM est maintenant entièrement centralisée dans jvm_session.


@pytest.fixture(scope="function")
def tweety_bridge_fixture(jvm_session):
    """
    Fournit une instance de TweetyBridge connectée à la session JVM gérée
    par la fixture jvm_session.
    """
    # La dépendance à jvm_session garantit que la JVM est démarrée avant
    # l'exécution de ce code.
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    logger.info("Création de l'instance TweetyBridge pour la fixture...")

    # Vérification explicite que la JVM est bien démarrée par la session
    assert (
        jpype.isJVMStarted()
    ), "La fixture jvm_session n'a pas réussi à démarrer la JVM."

    bridge = TweetyBridge()
    assert (
        bridge.initializer.is_jvm_ready()
    ), "La JVM devrait être prête grâce à jvm_session"
    logger.info("Instance TweetyBridge créée avec succès.")
    yield bridge


# Charger les fixtures définies dans d'autres fichiers comme des plugins
pytest_plugins = [
    "tests.fixtures.jvm_subprocess_fixture",
    "tests.spinning_threads",
    "pytest_playwright",
]

# --- Chargement conditionnel des fixtures lourdes ---
# Ne charge les fixtures d'intégration (qui dépendent de la JVM) que si
# la session JVM n'est pas explicitement désactivée.
# Cela évite à pytest de tenter de résoudre la fixture jvm_session
# lorsque nous savons qu'elle ne sera pas disponible.
import pytest

_disable_jvm = _jvm_session_disabled()

if not _disable_jvm:
    pytest_plugins.append("tests.fixtures.integration_fixtures")
else:
    # Utilise print pour s'assurer que le message est visible même si le logging n'est pas encore configuré
    print(
        "\n[INFO] Fixtures d'intégration (integration_fixtures.py) non chargées en raison de l'option --disable-jvm-session."
    )
    # Utilise print pour s'assurer que le message est visible même si le logging n'est pas encore configuré
    print(
        "\n[INFO] Fixtures d'intégration (integration_fixtures.py) non chargées en raison de l'option --disable-jvm-session."
    )


@pytest.fixture(scope="function", autouse=True)
def check_mock_llm_is_forced(request, monkeypatch):
    """
    Ce "coupe-circuit" est une sécurité pour tous les tests.
    Désactive les mocks pour les tests LLM réels (real_llm, llm_light, llm_integration, llm_critical).
    """
    from argumentation_analysis.config.settings import settings

    # Détection des markers LLM réels (anciens + nouveaux harmonisés)
    llm_markers = {"real_llm", "llm_light", "llm_integration", "llm_critical"}
    has_llm_marker = any(marker in request.node.keywords for marker in llm_markers)

    if has_llm_marker:
        marker_found = next(m for m in llm_markers if m in request.node.keywords)
        logger.warning(
            f"Le test {request.node.name} utilise le marqueur '{marker_found}'. Le mock LLM est désactivé."
        )
        monkeypatch.setattr(settings, "MOCK_LLM", False)
        monkeypatch.setattr(settings, "use_mock_llm", False)
        yield
    else:
        monkeypatch.setattr(settings, "MOCK_LLM", True)
        monkeypatch.setattr(settings, "use_mock_llm", True)
        yield


def pytest_collection_modifyitems(config, items):
    """
    Auto-marque les tests utilisant semantic_kernel avec marker llm_integration.

    Résout régression: Introduction markers llm_* sans migration complète.
    Restaure centaines tests semantic_kernel désactivés depuis juin 2025.

    Mission D3.2 - Réincorporation Tests LLM Baseline Niveau 2
    """
    import os

    for item in items:
        # Récupérer fichier source du test
        test_file = str(item.fspath)

        # Vérifier si test a déjà un marker llm_*
        has_llm_marker = any(
            marker.name in {"llm_light", "llm_integration", "llm_critical"}
            for marker in item.iter_markers()
        )

        # Si pas de marker llm_*, vérifier imports semantic_kernel
        if not has_llm_marker and os.path.exists(test_file):
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Détection imports semantic_kernel
                if "semantic_kernel" in content or "from semantic_kernel" in content:
                    # Auto-marquer avec llm_integration par défaut
                    item.add_marker(pytest.mark.llm_integration)

            except Exception as e:
                # En cas d'erreur lecture, ignorer silencieusement
                pass


@pytest.fixture(scope="session")
def backend_url(request):
    """Provides the backend URL from command-line options."""
    return request.config.getoption("--backend-url")


@pytest.fixture
def mock_kernel():
    """
    Provides a mocked Semantic Kernel that is compatible with Pydantic validation.
    It returns a real Kernel instance with a mocked chat completion service.
    """
    try:
        import semantic_kernel as sk
        from argumentation_analysis.core.llm_service import MockChatCompletion
    except ImportError:
        pytest.fail(
            "Failed to import semantic_kernel or MockChatCompletion for mock_kernel fixture."
        )

    kernel = sk.Kernel()
    mock_service = MockChatCompletion(
        service_id="mock_service", ai_model_id="mock_model"
    )
    kernel.add_service(mock_service)

    # Conserver une certaine compatibilité avec l'ancien mock pour les plugins si nécessaire
    kernel.plugins = MagicMock()
    mock_plugin = MagicMock()
    mock_function = MagicMock()
    mock_function.invoke.return_value = '{"formulas": ["exists X: (Cat(X))"]}'
    mock_plugin.__getitem__.return_value = mock_function
    kernel.plugins.__getitem__.return_value = mock_plugin

    return kernel


@pytest.fixture
def fol_agent(mock_kernel):
    """Provides a concrete, testable instance of FOLLogicAgent."""

    class ConcreteFOLAgent(FOLLogicAgent):
        async def validate_argument(
            self, premises: list[str], conclusion: str, **kwargs
        ) -> bool:
            return True

    agent = ConcreteFOLAgent(kernel=mock_kernel, agent_name="fol_test_agent")
    agent._tweety_bridge = MagicMock()
    agent._tweety_bridge.validate_fol_belief_set.return_value = (True, "Valid")
    return agent


@pytest.fixture
def sample_definitions():
    """Provides a sample ExtractDefinitions object for tests."""
    from argumentation_analysis.models.extract_definition import (
        Extract,
        SourceDefinition,
        ExtractDefinitions,
    )

    extract = Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="T{0}",
    )
    source = SourceDefinition(
        source_name="Test Source",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[extract],
    )
    return ExtractDefinitions(sources=[source])


@pytest.fixture
def mock_parse_args(mocker):
    """Fixture to mock argparse.ArgumentParser.parse_args."""
    return mocker.patch("argparse.ArgumentParser.parse_args")


@pytest.fixture
def successful_simple_argument_analysis_fixture_path(tmp_path):
    """
    Creates a temporary JSON file for testing the successful
    analysis of a simple argument.
    """
    data = {
        "text": "Socrates is a man, all men are mortal, therefore Socrates is mortal.",
        "analysis_mode": "simple",
    }
    file_path = tmp_path / "simple_argument.json"
    file_path.write_text(json.dumps(data))
    return str(file_path)


@pytest.fixture(scope="function")
def page_with_console_logs(page: "Page"):
    """
    Wraps the Playwright page to automatically log console messages,
    especially JS errors.
    """

    def handle_console_message(msg):
        # Filtrer pour ne montrer que les messages pertinents (erreurs, warnings)
        if msg.type.lower() in ["error", "warning"]:
            print(f"\n[CONSOLE {msg.type.upper()}] {msg.text}")
            # Si c'est une erreur, afficher la pile d'appels si disponible
            if msg.location:
                print(
                    f"    at {msg.location['url']}:{msg.location['lineNumber']}:{msg.location['columnNumber']}"
                )

    page.on("console", handle_console_message)
    yield page
    # Le nettoyage se fait automatiquement à la fin du test
    page.remove_listener("console", handle_console_message)


# --- Gestion des Serveurs E2E ---

import subprocess
import time
from urllib.parse import urlparse

import requests


def _server_output(process: subprocess.Popen, log_path=None) -> str:
    """What the server printed.

    The e2e fixture sends the server's output to a log file, so
    ``communicate()`` returns ``(None, None)``: the log is then the only place
    that names why the server stopped (#2480).
    """
    if log_path is not None:
        try:
            return Path(log_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"<log {log_path} unreadable: {exc}>"
    stdout, stderr = process.communicate(timeout=5)
    return "\n".join(
        part.decode("utf-8", "ignore") for part in (stdout, stderr) if part is not None
    )


def _wait_for_server(
    url: str,
    process: subprocess.Popen,
    timeout: int = 120,
    log_path=None,
    path: str = "/api/health",
):
    """Attend qu'un serveur soit disponible ou que le processus se termine.

    ``log_path`` : le fichier où le serveur écrit sa sortie, s'il y en a un.
    ``path`` : ce que la sonde demande, ``/api/health`` au backend, ``/`` au
    frontend (#2548).
    """
    start_time = time.time()
    try:
        while time.time() - start_time < timeout:
            # Vérifie si le processus a terminé prématurément
            if process.poll() is not None:
                # Le serveur s'est arrêté, on lève une erreur avec sa sortie
                output = _server_output(process, log_path)

                # Utiliser le logger pour s'assurer que la sortie est capturée par pytest
                logger.error(
                    f"Le serveur {url} a terminé prématurément. Code: {process.poll()}"
                )
                logger.error(f"--- SORTIE DU SERVEUR ---\n{output}")

                raise RuntimeError(
                    f"Le serveur à l'adresse {url} a terminé prématurément avec le code {process.poll()}.\n"
                    f"Sortie du serveur :\n{output}"
                )

            try:
                response = requests.get(f"{url}{path}", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Serveur à l'adresse {url} est prêt !")
                    return True
            except requests.ConnectionError:
                time.sleep(2)  # Attend un peu avant de réessayer
            except requests.Timeout:
                logger.warning(f"Timeout lors de la connexion à {url}. Réessai...")

        # Si la boucle se termine, c'est un timeout
        raise TimeoutError(
            f"Le serveur à l'adresse {url} n'a pas démarré dans le temps imparti de {timeout}s."
            + (
                f"\nSortie du serveur :\n{_server_output(process, log_path)[-3000:]}"
                if log_path is not None
                else ""
            )
        )
    finally:
        # Dans tous les cas (succès, exception), si le processus est toujours en vie mais que
        # la fonction se termine (par ex. timeout), on essaie de récupérer sa sortie.
        if process.poll() is None:
            logger.info(
                "Le processus serveur est toujours en cours d'exécution après la fin de la vérification."
            )
        else:
            # S'il y a eu un timeout et que le processus s'est terminé entre-temps,
            # on tente une dernière fois de récupérer sa sortie pour le débogage.
            try:
                output = _server_output(process, log_path)
                logger.error(f"SORTIE DU SERVEUR CAPTURÉE APRÈS TIMEOUT:\n{output}")
            except subprocess.TimeoutExpired:
                logger.error(
                    "Impossible de récupérer la sortie du processus serveur après le timeout (il est peut-être bloqué)."
                )
            except Exception as e:
                logger.error(
                    f"Une erreur est survenue en tentant de récupérer la sortie du serveur après timeout: {e}"
                )


def _e2e_backend_command(host: str, port: str) -> list:
    """The e2e backend: the live FastAPI app, served by uvicorn (#2480).

    ``services.web_api_from_libs.app``, the Flask app this fixture used to
    start, was archived in df031b34 (#34). ``api.main:app`` is the target the
    #1853 launchers converged on.
    """
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]


def _e2e_backend_env(port: str, project_root: Path) -> dict:
    """The e2e backend's environment: this process's, plus the keys the
    fixture decides.

    ``ensure_env()`` has already loaded the root ``.env`` into ``os.environ``
    and kept every value the caller set (#2472). This fixture used to read the
    ``.env`` a second time and overwrite those values, an emptied key included
    (#2480).
    """
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["PYTHONPATH"] = str(project_root)
    return env


# Where the React app lives; ``npm run build`` writes ``build/`` there, and
# ``interface_web/app.py`` serves that directory (``STATIC_FILES_DIR``).
_E2E_FRONTEND_DIR = Path("services") / "web_api" / "interface-web-argumentative"


def _e2e_frontend_command(host: str, port: str) -> list:
    """The e2e frontend: the Starlette app that serves the React build and
    relays ``/api/*`` to the backend, which is what users get (#2548).

    The fixture used to run ``npm start``, the React dev server. The e2e lane
    never installed it, and the fixture slept 15 s and yielded a URL that
    nothing answered: 25 pages refused the connection (run 35969872851).
    """
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "interface_web.app:app",
        "--host",
        host,
        "--port",
        str(port),
    ]


def _e2e_frontend_env(backend_url: str, project_root: Path) -> dict:
    """The e2e frontend's environment: the backend it relays ``/api/*`` to."""
    backend = urlparse(backend_url)
    env = os.environ.copy()
    env["FASTAPI_HOST"] = backend.hostname or "127.0.0.1"
    env["FASTAPI_PORT"] = str(backend.port)
    env["PYTHONPATH"] = str(project_root)
    return env


def _e2e_frontend_build(project_root: Path) -> Path:
    """The ``index.html`` of the React build. Raises if there is none: the
    build is not in git, and the app would answer 404 to every page."""
    index = project_root / _E2E_FRONTEND_DIR / "build" / "index.html"
    if not index.is_file():
        raise RuntimeError(
            f"The e2e frontend has no build: {index} is missing. Run "
            f"`npm ci` then `npm run build` in {_E2E_FRONTEND_DIR.as_posix()}; "
            "the e2e lane does (#2548)."
        )
    return index


def _start_e2e_frontend(frontend_url, backend_url, project_root, logs_dir):
    """Start the e2e frontend and wait until it serves ``/``.
    ``(process, log_file)``.

    Raises if there is no build, or with the tail of the frontend's log if it
    exits or never answers; the process is stopped first (#2548).
    """
    _e2e_frontend_build(project_root)
    parsed = urlparse(frontend_url)
    command = _e2e_frontend_command(parsed.hostname or "127.0.0.1", str(parsed.port))
    log_path = Path(logs_dir) / "frontend_server.log"
    log_file = open(log_path, "w")
    logger.info(
        f"Démarrage du serveur frontend avec la commande: {' '.join(command)}"
        f". Logs dans: {log_path}"
    )
    process = subprocess.Popen(
        command,
        cwd=project_root,
        stdout=log_file,
        stderr=log_file,
        env=_e2e_frontend_env(backend_url, project_root),
    )
    try:
        _wait_for_server(frontend_url, process, log_path=log_path, path="/")
    except BaseException:
        _kill_process(process)
        log_file.close()
        raise
    return process, log_file


def _kill_process(proc):
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
            logger.info(f"Processus {proc.pid} terminé avec la méthode terminate().")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
            logger.warning(
                f"Processus {proc.pid} ne répondait pas, il a été tué (kill)."
            )
        except Exception as e:
            logger.error(f"Erreur en terminant le processus {proc.pid}: {e}")


@pytest.fixture(scope="session")
def e2e_servers(request):
    """
    Fixture de session qui démarre et gère les serveurs backend et frontend pour les tests E2E.
    Elle utilise `subprocess.Popen` et garantit l'arrêt des serveurs à la fin.
    """
    if request.config.getoption("--disable-e2e-servers-fixture"):
        logger.info("Fixture e2e_servers désactivée via l'option en ligne de commande.")
        yield None, None
        return

    backend_url = request.config.getoption("--backend-url")
    frontend_url = request.config.getoption("--frontend-url")
    project_root = Path(__file__).parent.parent

    backend_process = None
    frontend_process = None

    try:
        # --- Démarrage du serveur Backend (api.main:app, #2480) ---
        parsed_backend_url = urlparse(backend_url)
        backend_port = str(parsed_backend_url.port)
        backend_command = _e2e_backend_command(
            parsed_backend_url.hostname or "127.0.0.1", backend_port
        )
        backend_env = _e2e_backend_env(backend_port, project_root)

        logger.info(
            f"Démarrage du serveur backend avec la commande: {' '.join(backend_command)}"
        )
        # Création des fichiers de log
        e2e_logs_dir = project_root / "_e2e_logs"
        e2e_logs_dir.mkdir(exist_ok=True)
        backend_log_path = e2e_logs_dir / "backend_server.log"
        backend_log_file = open(backend_log_path, "w")

        logger.info(f"Démarrage du serveur backend. Logs dans: {backend_log_path}")
        backend_process = subprocess.Popen(
            backend_command,
            cwd=project_root,
            stdout=backend_log_file,
            stderr=backend_log_file,
            env=backend_env,
        )

        # Attendre que le backend soit prêt
        _wait_for_server(backend_url, backend_process, log_path=backend_log_path)

        # --- Démarrage du serveur Frontend (interface_web.app:app, #2548) ---
        frontend_process, frontend_log_file = _start_e2e_frontend(
            frontend_url, backend_url, project_root, e2e_logs_dir
        )

        yield backend_url, frontend_url

    finally:
        logger.info("--- Nettoyage de la fixture e2e_servers ---")
        _kill_process(frontend_process)
        if "frontend_log_file" in locals() and not frontend_log_file.closed:
            frontend_log_file.close()

        _kill_process(backend_process)
        if "backend_log_file" in locals() and not backend_log_file.closed:
            backend_log_file.close()

        logger.info("Serveurs E2E terminés.")
