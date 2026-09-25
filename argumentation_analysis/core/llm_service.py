# core/llm_service.py
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    AzureChatCompletion,
)
from typing import Any, Dict, Optional, Union, AsyncGenerator, List, Tuple
import httpx
from openai import AsyncOpenAI
import json
import asyncio
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Tentative de correction en supprimant l'import qui échoue
# from semantic_kernel.contents.tool_call_content import ToolCallContent
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.const import DEFAULT_SERVICE_NAME
from argumentation_analysis.core.utils.network_utils import get_resilient_async_client
from argumentation_analysis.config.settings import settings, DEFAULT_CHAT_MODEL_ID

# Logger pour ce module
logger = logging.getLogger("Orchestration.LLM")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
logger.info("<<<<< MODULE llm_service.py LOADED >>>>>")


# Modèles retirés : toute résolution les remplace, quelle que soit la source
# (.env, argument explicite). #1930 (décision user 2026-08-28) : gpt-5-mini
# dépense ~81 % de ses tokens en raisonnement invisible — 11× le coût de luna
# par tâche rendue — et tombe dans le piège #1929 (contenu vide en HTTP 200
# quand le budget de sortie est serré, car le raisonnement se sert en premier).
OBSOLETE_MODEL_SUBSTITUTIONS = {
    "gpt-4-32k": DEFAULT_CHAT_MODEL_ID,
    "gpt-5-mini": DEFAULT_CHAT_MODEL_ID,
    "openai/gpt-5-mini": f"openai/{DEFAULT_CHAT_MODEL_ID}",
}


def substitute_obsolete_model(
    model_id: str, env_var_hint: str = "OPENAI_CHAT_MODEL_ID"
) -> str:
    """Replace a retired model id, naming the .env line to update."""
    new_model_id = OBSOLETE_MODEL_SUBSTITUTIONS.get(model_id)
    if new_model_id is None:
        return model_id
    logger.warning(
        f"Le modèle '{model_id}' est obsolète ou inaccessible. "
        f"Substitution automatique par '{new_model_id}'. "
        f"Veuillez mettre à jour votre fichier .env avec {env_var_hint}={new_model_id}"
    )
    return new_model_id


# Sampling-params policy (#1936): reasoning-model families (gpt-5*, o1*, o3*)
# reject temperature/seed (and the max_tokens spelling) with a 400 BadRequest.
# Routing was centralized in resolve_chat_endpoint; these helpers centralize
# the sampling side so raw-SDK callers consult ONE policy instead of
# hardcoding params at each call site. They live in core (not orchestration)
# because adapters and specialists must be able to import them without an
# adapter→orchestrator cycle.
REASONING_MODEL_PREFIXES: Tuple[str, ...] = (
    "gpt-5",
    "o1",
    "o3",
    "openai/gpt-5",
    "openai/o1",
    "openai/o3",
)


def resolve_active_model_id() -> str:
    """The active chat model id — resolved by the canonical resolver (#2352).

    Was a hand-copied mirror of the OpenRouter toggle, and reproduced both
    divergences the #2352 audit measured: it skipped the
    ``OPENAI_CHAT_MODEL_ID`` jump when only OpenRouter is configured (rendering
    the default literal instead of the configured model) **and** the #1930
    obsolescence substitution, so it could name a model the canonical route had
    already replaced. Measured on the prescribed seat (only
    ``OPENAI_CHAT_MODEL_ID`` set, to an obsolete id): this returned
    ``gpt-5-mini`` while :func:`resolve_chat_endpoint` returned
    ``gpt-5.6-luna``.

    Delegation is the repair — the model id, the substitution and the single
    log line live in :func:`resolve_chat_endpoint` and nowhere else.
    """
    return resolve_chat_endpoint()[2]


def is_reasoning_model(model_id: str) -> bool:
    """Return True if *model_id* belongs to a known reasoning-model family."""
    lower = model_id.lower()
    return any(lower.startswith(p) for p in REASONING_MODEL_PREFIXES)


def get_determinism_params(model_id: Optional[str] = None) -> Dict[str, Any]:
    """Read determinism settings from environment variables.

    Supports two modes:
    - LLM_DETERMINISTIC_MODE=1: shorthand for temperature=0, seed=42
    - LLM_TEMPERATURE / LLM_SEED: fine-grained overrides (take precedence)

    When the model is a known reasoning model (gpt-5*, o1*, o3*),
    temperature/seed are suppressed unless ``LLM_FORCE_SAMPLING_PARAMS=1`` is set,
    because reasoning models typically reject those parameters with a 400 BadRequest.

    Args:
        model_id: the model id the caller will actually send this request to
            (e.g. the id returned by ``resolve_chat_endpoint``). When omitted,
            the active model is resolved from the environment — the historical
            behavior of the orchestration call sites.

    Returns a dict suitable for merging into ``client.chat.completions.create()``.
    """
    params: Dict[str, Any] = {}
    if os.environ.get("LLM_DETERMINISTIC_MODE"):
        params["temperature"] = 0.0
        params["seed"] = 42
    temp_str = os.environ.get("LLM_TEMPERATURE")
    if temp_str is not None:
        try:
            params["temperature"] = float(temp_str)
        except ValueError:
            pass
    seed_str = os.environ.get("LLM_SEED")
    if seed_str is not None:
        try:
            params["seed"] = int(seed_str)
        except ValueError:
            pass

    effective_model = model_id if model_id is not None else resolve_active_model_id()
    if params and is_reasoning_model(effective_model):
        if os.environ.get("LLM_FORCE_SAMPLING_PARAMS"):
            logger.warning(
                "Determinism params forced on reasoning model '%s' — may 400.",
                effective_model,
            )
        else:
            logger.warning(
                "Determinism requested but reasoning model '%s' does not support "
                "temperature/seed — params suppressed. Set LLM_FORCE_SAMPLING_PARAMS=1 "
                "to override.",
                effective_model,
            )
            params = {}

    return params


def _log_resolved_llm_config(
    api_key: str, base_url: str, model_id: str, source: str
) -> None:
    """Log the resolved LLM config in one line — makes silent divergence visible (#2281).

    Also the single funnel for the declared-route guard (#2322): every
    resolution site in this module logs through here, so the assertion lives
    here and covers them all — the log line is emitted BEFORE the guard
    raises, so a divergent run leaves the evidence in its log.

    Args:
        api_key: the resolved key (empty means none configured)
        base_url: the resolved endpoint
        model_id: the resolved model id
        source: human-readable origin (e.g. "OPENROUTER_API_KEY+OPENROUTER_BASE_URL", "OPENAI_API_KEY")

    Raises:
        LLMRouteDivergenceError: when ``LLM_EXPECTED_ROUTE`` is declared and
            the resolved route diverges from it (see
            :func:`assert_declared_route`).
    """
    provider = "OpenRouter" if base_url and "openrouter" in base_url else "OpenAI"
    logger.info(
        "LLM config resolved: provider=%s endpoint=%s model=%s source=%s key=%s",
        provider,
        base_url or "(default)",
        model_id,
        source,
        "present" if api_key else "ABSENT",
    )
    assert_declared_route(base_url, model_id, source)


class LLMRouteDivergenceError(RuntimeError):
    """The declared canonical route and the resolved route disagree (#2322).

    Raised by :func:`assert_declared_route` when ``LLM_EXPECTED_ROUTE`` is
    declared and the environment resolves elsewhere — the failure mode where
    a lane carrying only ``OPENAI_API_KEY`` silently routes to
    api.openai.com and dies later in scattered 400s instead of one named
    error at startup. The guard never reroutes: fix the environment or the
    declaration.
    """


_EXPECTED_ROUTE_ENV = "LLM_EXPECTED_ROUTE"


def classify_route(base_url: str) -> str:
    """Classify a resolved endpoint the way the log line presents it.

    Same heuristic as ``_log_resolved_llm_config``: an OpenRouter substring
    reads as ``openrouter``, everything else as the OpenAI-compatible default
    (``openai``) — including custom local endpoints, which simply never
    declare ``LLM_EXPECTED_ROUTE`` and are unaffected.

    Public since #2352: the migrated route consumers
    (``orchestration.invoke_callables._resolve_llm_route``) used to spell the
    provider label themselves; the vocabulary belongs to this module.
    """
    return "openrouter" if base_url and "openrouter" in base_url else "openai"


def assert_declared_route(base_url: str, model_id: str, source: str) -> None:
    """Assert the resolved route matches the DECLARED canonical route (#2322).

    The declaration is opt-in via ``LLM_EXPECTED_ROUTE``, set by the run that
    requires a specific route (a CI lane, a benchmark harness) — it is never
    hardcoded for everyone, so local runs on other routes are unaffected:

    - unset → no-op (behavior unchanged);
    - empty string → WARNING + no-op (#2281 — empty ≠ absent);
    - ``openrouter`` or ``openrouter:<model_id>`` → the resolved provider
      (and model, when declared) MUST match, else :class:`LLMRouteDivergenceError`
      naming both sides. Never auto-corrects.

    Args:
        base_url: the resolved endpoint
        model_id: the resolved model id
        source: the resolution source, echoed in the error
    """
    raw = os.environ.get(_EXPECTED_ROUTE_ENV)
    if raw is None:
        return
    declared = raw.strip()
    if not declared:
        logger.warning(
            "%s is set to an empty string (#2281) — treated as not declared. "
            "Remove the line from the environment (empty ≠ absent).",
            _EXPECTED_ROUTE_ENV,
        )
        return
    declared_provider, _, declared_model = declared.lower().partition(":")
    resolved_provider = classify_route(base_url)
    mismatches = []
    if declared_provider != resolved_provider:
        mismatches.append(
            f"provider declared={declared_provider} resolved={resolved_provider}"
        )
    if declared_model and model_id and model_id.lower() != declared_model:
        mismatches.append(f"model declared={declared_model} resolved={model_id}")
    if mismatches:
        raise LLMRouteDivergenceError(
            f"LLM route divergence (#2322): {'; '.join(mismatches)} — "
            f"endpoint={base_url or '(default)'} source={source}. The "
            f"declaration ({_EXPECTED_ROUTE_ENV}={declared}) and the environment "
            "resolve to different routes. Fix the environment or the "
            "declaration — this guard never reroutes."
        )


def resolve_chat_endpoint(
    default_model: str = DEFAULT_CHAT_MODEL_ID,
) -> Tuple[str, str, str]:
    """Resolve the chat endpoint honoring the OpenRouter toggle.

    Single canonical source of truth for routing raw-SDK (non-kernel) LLM
    chat calls — the ONE route resolver since #2352. ``create_llm_service``
    (this module) embeds the same toggle for the kernel path, and every
    non-kernel caller DELEGATES here rather than re-deriving it:
    ``resolve_active_model_id``, ``orchestration.invoke_callables._resolve_llm_route``,
    ``plugins.coordinated_logic_plugin._get_openai_client``,
    ``services.nl_to_logic._translate_with_llm`` and
    ``services.ai_shield.layers.llm_validator.LLMValidatorLayer``. A copy that
    re-implements the toggle diverges silently — that is the defect #2352
    measures, not a style preference.
    Anti-pendule (#1019 / anti-théâtre): consults ``OPENROUTER_BASE_URL`` +
    ``OPENROUTER_API_KEY`` first and falls back to ``OPENAI_*``. Do NOT add a
    new knob — every raw-SDK caller must go through this so they no longer hit
    the official OpenAI quota (→ 429 → silent fallback) when OpenRouter is on.

    Args:
        default_model: model id used when neither ``OPENROUTER_CHAT_MODEL_ID``
            nor ``OPENAI_CHAT_MODEL_ID`` is set.

    Returns:
        ``(api_key, base_url, model_id)``. ``api_key`` is ``""`` when no key
        is configured (callers treat this as "no LLM available"). When the
        OpenRouter toggle is on, ``base_url`` is the OpenRouter endpoint and
        ``model_id`` is the provider-prefixed ``OPENROUTER_CHAT_MODEL_ID``.

    An explicitly-set-but-empty value is treated as not configured, with a
    WARNING naming the variable (#2281 — empty ≠ absent, the drift must be
    visible without turning "no LLM" into a crash; probes degrade, the
    startup factory :func:`create_llm_service` refuses).
    """
    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_base_url and openrouter_api_key:
        api_key = openrouter_api_key
        base_url = openrouter_base_url
        model_id = os.environ.get(
            "OPENROUTER_CHAT_MODEL_ID",
            os.environ.get("OPENAI_CHAT_MODEL_ID", default_model),
        )
        model_id = substitute_obsolete_model(model_id, "OPENROUTER_CHAT_MODEL_ID")
        _log_resolved_llm_config(
            api_key, base_url, model_id, "OPENROUTER_API_KEY+OPENROUTER_BASE_URL"
        )
        return api_key, base_url, model_id
    raw_key = os.environ.get("OPENAI_API_KEY")
    if raw_key is not None and raw_key.strip() == "":
        logger.warning(
            "OPENAI_API_KEY is set to an empty string (#2281) — treated as not "
            "configured. Remove the line from .env (empty ≠ absent)."
        )
    api_key = raw_key or ""
    raw_base_url = os.environ.get("OPENAI_BASE_URL")
    if raw_base_url is not None and raw_base_url.strip() == "":
        logger.warning(
            "OPENAI_BASE_URL is set to an empty string (#2281) — using the "
            "default endpoint. Remove the line from .env (empty ≠ absent)."
        )
        raw_base_url = None
    base_url = raw_base_url or "https://api.openai.com/v1"
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", default_model)
    model_id = substitute_obsolete_model(model_id)
    _log_resolved_llm_config(api_key, base_url, model_id, "OPENAI_API_KEY")
    return api_key, base_url, model_id


# service_id a un défaut : l'id par défaut de Semantic Kernel, celui que
# BaseAgent résout sans id explicite. fdbb54e20 l'avait rendu obligatoire sans
# motif écrit, et onze appelants (code, docs, notebook) comptaient encore sur
# un défaut : chacun levait TypeError (#2634).
def create_llm_service(
    service_id: str = DEFAULT_SERVICE_NAME,
    model_id: Optional[str] = None,
    service_type: str = "OpenAIChatCompletion",
    force_mock: bool = False,
    force_authentic: bool = False,
) -> Union[OpenAIChatCompletion, AzureChatCompletion, "ChatCompletionClientBase"]:
    """
    Factory pour créer et configurer une instance de service de complétion de chat.

    Cette fonction lit la configuration à partir des variables d'environnement
    pour déterminer quel service instancier (OpenAI standard ou Azure OpenAI).
    Elle peut également forcer la création d'un service mocké ou authentique
    pour les tests.

    Args:
        service_id (str): L'ID de service à utiliser pour l'instance dans
                          le kernel Semantic Kernel. Par défaut "default"
                          (``semantic_kernel.const.DEFAULT_SERVICE_NAME``).
        model_id (str, optionnel): L'ID du modèle. Si non fourni, il est lu
                                 depuis la variable d'environnement OPENAI_CHAT_MODEL_ID.
        service_type (str): Le type de service à créer (par ex., "OpenAIChatCompletion").
        force_mock (bool): Si True, retourne une instance de MockChatCompletion.
        force_authentic (bool): Si True, force la création d'un service authentique
                                même dans un environnement de test.

    Returns:
        Instance configurée du service de chat.

    Raises:
        ValueError: Si la configuration requise est manquante.
        RuntimeError: Si la création du service échoue.
    """
    logger.critical("<<<<< create_llm_service FUNCTION CALLED >>>>>")
    logger.info(f"--- Configuration du Service LLM ({service_id}) ---")

    # Gestion des mocks pour les tests
    # force_authentic overrides force_mock and test environment detection
    is_test_environment = "PYTEST_CURRENT_TEST" in os.environ
    if not force_authentic and (force_mock or is_test_environment):
        if force_mock:
            logger.warning(
                f"Création forcée d'un service LLM MOCKÉ pour '{service_id}'."
            )
        else:
            logger.warning(
                f"Environnement de test détecté. Création d'un service LLM MOCKÉ pour '{service_id}'."
            )
        # Lazy import to avoid requiring test modules in production code
        from tests.mocks.llm_service_mocks import MockChatCompletion

        return MockChatCompletion(service_id=service_id, ai_model_id="mock_model")

    logger.info("Tentative de création d'un service LLM AUTHENTIQUE...")

    # Si on n'est pas en mode mock, on cherche le model_id s'il n'est pas fourni
    if not model_id:
        # Le repli vient du MÊME endroit que celui du résolveur (#2377, item 4)
        # — ce site portait une 2ᵉ copie du littéral, c'est-à-dire un 2ᵉ défaut
        # libre de diverger du premier sans que rien ne rougisse.
        model_id = os.getenv("OPENAI_CHAT_MODEL_ID", DEFAULT_CHAT_MODEL_ID)
        logger.info(
            f"model_id non fourni, utilisation de la valeur de .env: {model_id}"
        )

    # Correction automatique pour les modèles obsolètes (table partagée #1930)
    model_id = substitute_obsolete_model(model_id)
    # --- Sélection du provider : bascule OpenRouter si configurée ---
    # Si OPENROUTER_BASE_URL est défini (+ OPENROUTER_API_KEY), les appels sont
    # routés vers OpenRouter (API compatible OpenAI). Sinon, le comportement
    # OpenAI officiel reste inchangé. Toggle réversible : retirer
    # OPENROUTER_BASE_URL du .env pour revenir à OpenAI.
    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    use_openrouter = bool(openrouter_base_url and openrouter_api_key)

    if use_openrouter:
        api_key = openrouter_api_key
        # OpenRouter exige des slugs préfixés par le provider (ex. "openai/gpt-5-mini")
        model_id = substitute_obsolete_model(
            os.getenv("OPENROUTER_CHAT_MODEL_ID", model_id),
            "OPENROUTER_CHAT_MODEL_ID",
        )
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key == "":
            raise ValueError(
                "OPENAI_API_KEY is set to an empty string (#2281). "
                "Remove the line from .env or provide a real key — empty ≠ absent."
            )
    org_id = os.environ.get("OPENAI_ORG_ID")

    if not api_key:
        raise ValueError(
            "Aucune clé API LLM définie. Définissez OPENAI_API_KEY, ou "
            "OPENROUTER_API_KEY + OPENROUTER_BASE_URL pour router via OpenRouter."
        )

    # Log the resolved config so silent divergence is visible (#2281)
    _log_resolved_llm_config(
        api_key,
        openrouter_base_url or "https://api.openai.com/v1",
        model_id,
        (
            "OPENROUTER_API_KEY+OPENROUTER_BASE_URL"
            if use_openrouter
            else "OPENAI_API_KEY"
        ),
    )

    resilient_client = get_resilient_async_client()
    # Typed as the SK base so the authentic OpenAI/Azure instance, and the
    # cache wrapper (CachedChatCompletion) added below in record/replay mode,
    # are all valid assignments (BO-3 #1473 PR2).
    llm_instance: Union[ChatCompletionClientBase, None] = None

    try:
        if service_type == "OpenAIChatCompletion":
            provider_label = (
                "OpenRouter" if use_openrouter else "l'API OpenAI officielle"
            )
            logger.info(
                f"Configuration Service: OpenAIChatCompletion pour {provider_label}..."
            )

            client_kwargs = {"api_key": api_key, "http_client": resilient_client}
            if use_openrouter:
                client_kwargs["base_url"] = openrouter_base_url
            if org_id:
                client_kwargs["organization"] = org_id

            async_client = AsyncOpenAI(**client_kwargs)

            llm_instance = OpenAIChatCompletion(
                service_id=service_id, ai_model_id=model_id, async_client=async_client
            )
            logger.info(f"Service LLM OpenAI ({model_id}) créé avec succès.")

        # NOTE: La logique pour Azure est conservée mais non utilisée si service_type est OpenAIChatCompletion
        elif service_type == "AzureChatCompletion":
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                raise ValueError(
                    "La variable d'environnement AZURE_OPENAI_ENDPOINT est requise pour Azure."
                )

            logger.info("Configuration Service: AzureChatCompletion...")
            llm_instance = AzureChatCompletion(
                service_id=service_id,
                deployment_name=model_id,
                endpoint=endpoint,
                api_key=api_key,
            )
            logger.info(f"Service LLM Azure ({model_id}) créé.")
        else:
            raise ValueError(f"Type de service LLM non supporté: {service_type}")

    except ValueError as ve:
        logger.critical(f"Erreur de configuration LLM: {ve}")
        raise
    except Exception as e:
        logger.critical(
            f"Erreur critique lors de la création du service LLM: {e}", exc_info=True
        )
        raise RuntimeError(f"Impossible de configurer le service LLM: {e}")

    if not llm_instance:
        raise RuntimeError("La configuration du service LLM a échoué silencieusement.")

    # Cache-aware SK-service wrapping (BO-3 #1473, PR2 — SK-native path):
    # wrap the freshly built service with CachedChatCompletion so SK-native agent
    # calls (ChatCompletionAgent.invoke / AgentGroupChat.invoke — the
    # conversational & cluedo orchestration modes, which reach the OpenAI API
    # through the kernel service and BYPASS the direct-path funnel
    # ``_guarded_chat_completion`` wired in PR1) are replayed from the same disk
    # cache. Inert in off mode (no wrapping, zero behavior change); record
    # persists the response, replay raises ``LLMCacheMiss`` on a miss (fail-loud
    # — never a silent live call, anti-théâtre #1019). Mirrors
    # ``_guarded_chat_completion`` (PR1, direct path). Both layers share
    # CACHE_DIR, so one record run seeds every call site and one replay run
    # replays every call site (BO-3 determinism DoD).
    #
    # CachedChatCompletion overrides get_chat_message_contents (plural); the
    # singular variant delegates to it via ``self`` (SK base class, line 190),
    # so both non-streaming entry points are intercepted. Streaming is out of
    # scope (same boundary as the direct path).
    from argumentation_analysis.services.llm_cache import (
        OFF,
        CachedChatCompletion,
        get_cache_mode,
    )

    cache_mode = get_cache_mode()
    if cache_mode != OFF:
        llm_instance = CachedChatCompletion(inner=llm_instance, mode=cache_mode)
        logger.info(f"Service LLM SK wrappé avec cache (mode={cache_mode}).")

    return llm_instance


# Conserver la classe LLMService pour la compatibilité, bien que la logique principale
# soit maintenant dans la factory `create_llm_service`.
class LLMService:
    def __init__(self, llm_instance: ChatCompletionClientBase):
        self._llm_instance = llm_instance

    @property
    def llm(self) -> ChatCompletionClientBase:
        return self._llm_instance

    # La méthode `create_llm_service` est maintenant statique et à l'extérieur
    # pour une meilleure séparation des préoccupations.


# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.llm_service chargé.")
