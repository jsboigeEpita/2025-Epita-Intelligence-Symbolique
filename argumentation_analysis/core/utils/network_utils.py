# -*- coding: utf-8 -*-
"""
Utilitaires réseau pour le projet.

Ce module fournit des fonctions pour effectuer des opérations réseau,
principalement le téléchargement de fichiers depuis des URLs.
Il gère les exceptions courantes et permet de vérifier l'intégrité
des fichiers téléchargés via leur taille.
"""

import logging
import os
import re
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import httpx
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, TypeVar
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from pybreaker import (
    CBStateType,
    CircuitBreaker,
    CircuitBreakerError,
    CircuitOpenState,
)

from argumentation_analysis.config.settings import settings

logger = logging.getLogger(__name__)

# --- Configuration de la résilience ---

# 1. Disjoncteur (Circuit Breaker)
# Les paramètres sont maintenant lus depuis la configuration centrale.
network_breaker = CircuitBreaker(
    fail_max=settings.network.breaker_fail_max,
    reset_timeout=settings.network.breaker_reset_timeout,
)

# 2. Stratégie de rejeu (Retry) SYNCHRONE pour `requests`
retry_on_network_error = retry(
    stop=stop_after_attempt(settings.network.retry_stop_after_attempt),
    wait=wait_exponential(
        multiplier=settings.network.retry_wait_multiplier,
        min=settings.network.retry_wait_min,
        max=settings.network.retry_wait_max,
    ),
    retry=retry_if_exception_type(
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        )
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)

# 3. Stratégie de rejeu ASYNCHRONE pour `httpx`
async_retry_on_network_error = retry(
    stop=stop_after_attempt(settings.network.retry_stop_after_attempt),
    wait=wait_exponential(
        multiplier=settings.network.retry_wait_multiplier,
        min=settings.network.retry_wait_min,
        max=settings.network.retry_wait_max,
    ),
    retry=retry_if_exception_type(
        (
            httpx.RequestError,
            httpx.HTTPStatusError,
        )
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)


# --- #3435 — composition du budget de phase avec le retry du client ---
#
# Mesuré sur le panel cycle 2 : ``act1_framing`` complète en 13,3–38,6 s sur
# les 8 documents sains ; sur un document un appel s'est bloqué et le budget
# de phase (180 s, ``workflows.py``) a tué l'acte SANS retry — parce que les
# propres nombres du client ne composent pas : ``default_timeout`` = 90 s par
# requête × ``retry_stop_after_attempt`` = 3 avec backoff 2–10 s signifie
# qu'UN appel bloqué suivi d'UN rejeu demande au moins 90 + 2 + 90 = 182 s,
# soit plus que le budget. Un rejeu que le budget ne peut pas loger est une
# promesse que le client ne peut pas tenir.
#
# LA règle (UN seul endroit, pas trois constantes) : quand une phase publie
# son budget, chaque tentative transport est bornée pour qu'au moins un
# rejeu tienne dedans :
#
#     deadline_par_tentative = min(default_timeout,
#                                  max(plancher,
#                                      (budget - retry_wait_max - marge) / 2))
#
# Au budget de production (180 s) : (180 - 10 - 10) / 2 = 80 s — deux
# tentatives plus le pire backoff prennent 170 s ≤ 180 s, et 80 s reste 2×
# la pire durée saine mesurée (38,6 s), donc une exécution saine ne sent
# jamais la borne. La borne ne RELÈVE jamais un délai (min avec le défaut
# configuré) ; une phase sans budget garde le comportement d'aujourd'hui,
# octet pour octet.
#
# Le plancher n'existe que pour les petits budgets (témoin à l'échelle du
# test) : en production (≥ 120 s) il ne lie jamais. Un budget qui ne peut
# pas loger ``plancher + wait_min + plancher`` n'admet honnêtement aucun
# rejeu — l'observateur et le message d'échec le disent alors.

#: #3435 — plus petit délai par tentative qui reste une vraie tentative.
PHASE_ATTEMPT_FLOOR_SECONDS = 1.5
#: #3435 — la marge couvre l'ordonnancement et le temps hors transport de la
#: phase (construction du prompt, écriture d'état) que le budget paie aussi.
PHASE_COMPOSITION_MARGIN_SECONDS = 10.0

#: #3435 — le budget de la phase en cours, publié par l'exécuteur
#: (``workflow_dsl``) avant d'invoquer le provider. ``None`` = pas de budget
#: (comportement d'avant, inchangé).
phase_attempt_budget: ContextVar[Optional[float]] = ContextVar(
    "phase_attempt_budget", default=None
)

#: #3435 — observateur mutable partagé entre l'exécuteur (qui le crée) et le
#: transport (qui le remplit) : nombre de tentatives transport et délai
#: appliqué. L'exécuteur lit son propre dictionnaire après l'échec — le
#: contexte d'une tâche annulée ne se propage pas, mais la référence objet si.
phase_transport_observer: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "phase_transport_observer", default=None
)


def compose_attempt_deadline(
    phase_budget_seconds: float,
    default_timeout: Optional[float] = None,
    retry_wait_max: Optional[float] = None,
    floor: Optional[float] = None,
    margin: Optional[float] = None,
) -> float:
    """Le délai par tentative transport pour que UN rejeu tienne (#3435).

    C'est LA règle de composition — l'unique endroit où elle vit. Les
    défauts se lisent dans ``NetworkSettings`` (jamais trois constantes
    copiées) : ``default_timeout``, ``retry_wait_max``. Voir le bloc
    ``#3435`` ci-dessus pour les mesures qui l'étalonnent.
    """
    dt = (
        settings.network.default_timeout if default_timeout is None else default_timeout
    )
    wmax = (
        float(settings.network.retry_wait_max)
        if retry_wait_max is None
        else retry_wait_max
    )
    fl = PHASE_ATTEMPT_FLOOR_SECONDS if floor is None else floor
    mg = PHASE_COMPOSITION_MARGIN_SECONDS if margin is None else margin
    derived = (float(phase_budget_seconds) - wmax - mg) / 2.0
    return min(dt, max(fl, derived))


def _extension_read_deadline(value: Any) -> Optional[float]:
    """Le délai de lecture posé dans ``extensions["timeout"]``, s'il existe.

    httpx y met un ``httpx.Timeout`` (attributs) ; httpcore lit un mapping
    (``.get``) — les deux formes sont lues, aucune n'est fabriquée.
    """
    if value is None:
        return None
    attr = getattr(value, "read", None)
    if attr is not None:
        return float(attr)
    getter = getattr(value, "get", None)
    if getter is not None:
        try:
            got = getter("read")
        except Exception:
            return None
        return None if got is None else float(got)
    return None


#: The four keys httpcore reads from ``request.extensions["timeout"]``.
_HTTPCORE_TIMEOUT_KEYS = ("connect", "read", "write", "pool")


def _clamped_timeout_mapping(value: Any, deadline: float) -> Dict[str, Optional[float]]:
    """The ``extensions["timeout"]`` MAPPING with every component clamped (#3450).

    httpcore reads this extension with ``.get("pool")``, ``.get("connect")``,
    ``.get("write")``, ``.get("read")`` — a mapping, never an object. httpx
    itself writes ``Timeout.as_dict()`` there. Writing an ``httpx.Timeout``
    object instead made every clamped request raise ``AttributeError`` inside
    the connection pool, which the OpenAI SDK reports as « Connection
    error. »: on the cycle-3 panel, Acts I–III and the deep synthesis were
    lost on 9 documents out of 10.

    Each component only SHRINKS: a component the client set below the
    deadline keeps its value; a component left unbounded (``None``) gets the
    deadline, since the phase budget bounds it.
    """
    current: Dict[str, Optional[float]] = {key: None for key in _HTTPCORE_TIMEOUT_KEYS}
    if isinstance(value, httpx.Timeout):
        current.update(value.as_dict())
    elif value is not None and hasattr(value, "get"):
        for key in _HTTPCORE_TIMEOUT_KEYS:
            current[key] = value.get(key)
    return {
        key: deadline if (seconds is None or deadline < seconds) else seconds
        for key, seconds in current.items()
    }


class PhaseBudgetTransport(httpx.AsyncBaseTransport):
    """Borne chaque tentative au délai composé du budget de phase (#3435).

    Vit SOUS ``ResilientAsyncTransport`` : le rejeu tenacity rappelle
    ``handle_async_request`` à chaque tentative, donc la borne s'applique
    PAR TENTATIVE et non sur l'ensemble rejeué. Sans budget publié
    (contextvar ``None``), la requête passe inchangée.

    httpcore lit ``request.extensions["timeout"]`` à chaque requête — la
    réécriture ici est le mécanisme de la borne, et l'exception qu'elle
    produit (``httpx.ReadTimeout``, sous-classe de ``httpx.RequestError``)
    est rejeuable par tenacity.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport):
        self.transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        budget = phase_attempt_budget.get()
        observer = phase_transport_observer.get()
        if observer is not None:
            observer["attempts"] = int(observer.get("attempts", 0)) + 1
        if budget is not None:
            deadline = compose_attempt_deadline(budget)
            observer and observer.setdefault("attempt_deadline", deadline)
            timeout_extension = request.extensions.get("timeout")
            current = _extension_read_deadline(timeout_extension)
            if current is None or deadline < current:
                # La borne ne fait que RÉTRÉCIR — jamais relever un délai
                # que le client a posé plus petit. httpcore lit un MAPPING
                # (#3450) : jamais un objet ``httpx.Timeout``.
                request.extensions["timeout"] = _clamped_timeout_mapping(
                    timeout_extension, deadline
                )
        return await self.transport.handle_async_request(request)


# --- Fonctions Utilitaires Réseau ---


@retry_on_network_error
@network_breaker
def download_file(
    url: str, destination_path: Path, expected_size: Optional[int] = None
) -> bool:
    """
    Télécharge un fichier de manière robuste en utilisant une stratégie de rejeu et un disjoncteur.

    :param url: L'URL du fichier à télécharger.
    :param destination_path: Le chemin où sauvegarder le fichier.
    :param expected_size: La taille attendue du fichier en octets pour validation.
    :return: True si le téléchargement est réussi et validé, False sinon.
    :raises CircuitBreakerError: Si le disjoncteur est ouvert.
    :raises requests.exceptions.RequestException: Après épuisement des tentatives de rejeu.
    """
    try:
        logger.info(f"Début du téléchargement de {url} vers {destination_path}")
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        with requests.get(
            url, stream=True, timeout=settings.network.default_timeout
        ) as r:
            r.raise_for_status()
            with open(destination_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        actual_size = destination_path.stat().st_size
        logger.info(
            f"Fichier téléchargé : {destination_path} (Taille : {actual_size} octets)"
        )

        if expected_size is not None:
            if actual_size == expected_size:
                logger.info(
                    f"La taille du fichier téléchargé ({actual_size} octets) correspond à la taille attendue ({expected_size} octets)."
                )
                return True
            else:
                logger.error(
                    f"Erreur de taille : la taille du fichier téléchargé ({actual_size} octets) ne correspond pas à la taille attendue ({expected_size} octets)."
                )
                # Optionnel : supprimer le fichier si la taille ne correspond pas pour éviter d'utiliser un fichier corrompu.
                # try:
                #     os.remove(destination_path)
                #     logger.info(f"Fichier {destination_path} supprimé en raison d'une taille incorrecte.")
                # except OSError as ose:
                #     logger.error(f"Impossible de supprimer le fichier {destination_path} après erreur de taille: {ose}")
                return False
        return True

        actual_size = destination_path.stat().st_size
        logger.info(
            f"Fichier téléchargé : {destination_path} (Taille : {actual_size} octets)"
        )

        if expected_size is not None and actual_size != expected_size:
            logger.error(
                f"Erreur de taille : {actual_size} octets reçus, {expected_size} attendus."
            )
            return False

        return True

    except CircuitBreakerError:
        logger.critical(f"Disjoncteur OUVERT pour {url}. La requête est bloquée.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Erreur de téléchargement persistante pour {url} après plusieurs tentatives: {e}"
        )
        # Le nettoyage est géré par la logique de rejeu qui relance l'exception finale.
        if destination_path.exists():
            try:
                os.remove(destination_path)
            except OSError as ose:
                logger.error(
                    f"Impossible de nettoyer le fichier partiel {destination_path}: {ose}"
                )
        raise  # Fait remonter l'exception pour que Tenacity la gère
    except OSError as e:
        logger.error(f"Erreur IO pour le fichier {destination_path}: {e}")
        return False


# --- Fonctions Asynchrones pour httpx ---

import json


class LoggingHttpTransport(httpx.AsyncBaseTransport):
    """
    Transport HTTP asynchrone personnalisé pour `httpx` qui logge les détails
    des requêtes et des réponses.
    """

    def __init__(
        self, logger: logging.Logger, wrapped_transport: httpx.AsyncBaseTransport = None
    ):
        self.logger = logger
        self._wrapped_transport = wrapped_transport or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.logger.info(f"--- RAW HTTP REQUEST (LLM Service) ---")
        self.logger.info(f"  Method: {request.method}")
        self.logger.info(f"  URL: {request.url}")
        if request.content:
            try:
                content_bytes = await request.aread()
                request.stream._buffer = [content_bytes]  # Re-buffer for next transport
                json_content = json.loads(content_bytes.decode("utf-8"))
                pretty_json_content = json.dumps(
                    json_content, indent=2, ensure_ascii=False
                )
                self.logger.info(f"  Body (JSON):\n{pretty_json_content}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.logger.info(f"  Body: (Contenu non-JSON ou binaire)")

        response = await self._wrapped_transport.handle_async_request(request)

        self.logger.info(f"--- RAW HTTP RESPONSE (LLM Service) ---")
        self.logger.info(f"  Status Code: {response.status_code}")

        # La lecture du corps de la réponse a été désactivée car elle consomme
        # le flux et peut interférer avec la décompression (ex: brotli).
        # L'interception est désormais minimale pour éviter les effets de bord.

        # Le transport sous-jacent a déjà traité la réponse.
        # On peut inspecter les headers et le statut sans lire le corps.

        # Forcer la levée d'une exception pour les codes d'erreur (4xx, 5xx)
        # afin que le décorateur @retry de Tenacity puisse la traiter.
        if 400 <= response.status_code < 600:
            # Nous devons lire le corps ici UNIQUEMENT en cas d'erreur,
            # car l'exception en a besoin pour le message.
            # #2324 : ``response.raise_for_status()`` mourait en RuntimeError
            # (« request instance has not been set ») — une réponse de
            # transport nu n'a pas son request lié. Le 400 de l'API devenait
            # « APIConnectionError('Connection error.') » : le corps du
            # message — le param rejeté, la raison, le remède proposé par
            # l'API elle-même — se perdait, et le rejet se faisit passer pour
            # une panne réseau (retries openai inclus). Lever explicitement
            # avec le request et le corps : l'erreur dit ce que l'API a dit.
            await response.aread()
            raise httpx.HTTPStatusError(
                f"{response.status_code} {response.reason_phrase}: "
                f"{response.text[:500]}",
                request=request,
                response=response,
            )

        return response

    async def aclose(self) -> None:
        await self._wrapped_transport.aclose()


class ReasoningEffortTransport(httpx.AsyncBaseTransport):
    """#2324/#2827 — le paramètre que le connecteur SK ne peut pas exprimer,
    à la valeur que le modèle accepte.

    Mesuré le 22/09 (#2324) : ``gpt-5.6-luna`` (famille reasoning) rejette
    400 ``« Function tools with reasoning_effort are not supported … set
    reasoning_effort to 'none' »`` sur /v1/chat/completions dès qu'un appel
    porte des ``tools`` sans ``reasoning_effort`` explicite. SK 1.35 n'a pas
    le champ (extra ignoré — impossible à exprimer dans les settings) et SK
    1.44 ne l'envoie pas par défaut : le transport est le seul point de
    passage commun aux deux versions, et à tout appel à outils de la
    descente de taxonomie (chaque appel nav 400 → branche abandonnée → la
    descente vit en fallback silencieux ; une session d'enregistrement ne
    peut alors JAMAIS couvrir le rejeu).

    Même discipline que la politique brute ``get_determinism_params``
    (#1936) : n'injecter QUE si POST /chat/completions + ``tools`` présents
    + modèle reasoning (``is_reasoning_model``) + champ absent. Un appel
    sans tools ou un modèle non-reasoning ne doit pas recevoir le paramètre
    (l'API le rejette pour eux).

    #2827 (mesuré 28-29/09) : la valeur acceptée dépend du modèle. Le 'none'
    injecté est requis par ``gpt-5.6-luna`` avec tools, mais la famille
    o1/o3 le rejette (``« Unsupported value: 'none' is not supported with
    the 'o3-mini-2025-01-31' model. Supported values are: 'low', 'medium',
    and 'high'. »``, mesuré en direct sur la route canonique) alors que
    l'appel sans le champ passe 200. Le 400 « 'reasoning_effort' does not
    support 'none' » cité par l'issue venait du garde RA2 qui lisait les
    variables d'environnement brutes hors résolveur (#2352) : ``gpt-5-mini``
    y est retiré par ``OBSOLETE_MODEL_SUBSTITUTIONS`` (#1930) et la
    production n'envoie jamais cet id — mais ``o3-mini``/``o1``, eux, ne
    sont PAS retirés : un siège qui les configure passe inchangé par le
    résolveur, reçoit l'injection et la voit rejeter. Pas de table
    modèle→valeur (elle mentirait au prochain changement de modèle) : le
    400 du fournisseur décide, son message nomme soit la valeur à
    utiliser (``set reasoning_effort to 'X'``) soit les valeurs admises
    (valeur envoyée absente ⇒ champ retiré, le défaut du fournisseur
    reprend la main). Un seul rejeu adapté ; un second rejet se propage.

    **Provenance** : la correction ne touche qu'un champ que PERSONNE n'a
    exprimé — injecté par le transport, ou absent d'un modèle hors
    préfixes reasoning que le fournisseur exige quand même (directive).
    Une valeur posée par l'appelant se propage telle quelle (#1019 — le
    transport ne réécrit jamais un choix explicite). Le 400 arrive ici
    sous deux formes selon la chaîne : exception ``HTTPStatusError``
    (chaîne résiliente, où ``LoggingHttpTransport`` lève) ou réponse de
    statut 400 (chaîne nue de ``build_async_openai_client``) — les deux
    sont écoutées.
    """

    # Les 400 réels mesurés (#2827, #2840) : le remède nommé…
    _DIRECTIVE_RE = re.compile(r"set reasoning_effort to '([^']+)'", re.IGNORECASE)
    # …ou la liste des valeurs admises, épellée de deux façons (« values: »
    # sur la génération antérieure, « values are: » sur luna et o3).
    _SUPPORTED_RE = re.compile(r"supported values(?: are)?:\s*(.*)", re.IGNORECASE)
    # Le corps du 400 nomme le champ sous deux orthographes selon la
    # couche : « reasoning_effort » côté API directe, « reasoning.effort »
    # dans l'erreur OpenRouter enveloppée (mesuré sur le 400 o3-mini).
    _FIELD_MARKERS = ("reasoning_effort", "reasoning.effort")

    def __init__(self, wrapped_transport: httpx.AsyncBaseTransport):
        self._wrapped_transport = wrapped_transport

    @staticmethod
    def _effort_retry_value(
        rejection_text: str, sent_value: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Que faire d'un 400 nommant le champ ``reasoning_effort`` ?

        Retourne ``(rejouer, nouvelle_valeur)`` : ``nouvelle_valeur`` à
        ``None`` signifie retirer le champ ; ``(False, None)`` signifie ne
        pas réagir (le rejet n'offre aucune base de correction, ou la
        valeur absente ne donne rien à retirer — un rejeu au corps identique
        n'est pas une correction).
        """
        if not any(
            marker in rejection_text
            for marker in ReasoningEffortTransport._FIELD_MARKERS
        ):
            return False, None
        directive = ReasoningEffortTransport._DIRECTIVE_RE.search(rejection_text)
        if directive:
            return True, directive.group(1)
        supported = ReasoningEffortTransport._SUPPORTED_RE.search(rejection_text)
        if supported and sent_value is not None:
            values = re.findall(r"'([^']+)'", supported.group(1))
            if sent_value not in values:
                return True, None
        return False, None

    @staticmethod
    def _with_body(request: httpx.Request, body: Dict[str, Any]) -> httpx.Request:
        new_content = json.dumps(body, ensure_ascii=False).encode("utf-8")
        # Deux écritures, parce que deux lecteurs : le send
        # httpx consomme ``request.stream`` (_transports/
        # default.py passe ``content=request.stream`` au canal),
        # tandis que tout ``aread()`` en aval sert le cache
        # ``_content``. Écrire l'un sans l'autre et l'appel
        # part sur le fil avec l'ancien corps — mesuré #2324 :
        # l'idiome ``stream._buffer`` (hérité de LoggingHttp-
        # Transport) est un no-op sur le ByteStream de httpx
        # 0.28, qui n'a plus d'attribut ``_buffer``. Le flux de
        # remplacement vient d'une Request jetable — publique,
        # pas d'import privé.
        request.stream = httpx.Request("POST", request.url, content=new_content).stream
        request._content = new_content
        request.headers["content-length"] = str(len(new_content))
        return request

    async def _retry_adapted(
        self,
        request: httpx.Request,
        body: Dict[str, Any],
        sent_value: Optional[str],
        new_value: Optional[str],
    ) -> httpx.Response:
        """Un seul rejeu au corps adapté ; le verdict du second essai
        remonte tel quel (réponse ou exception du niveau enveloppé)."""
        model = body.get("model", "?")
        if new_value is None:
            body.pop("reasoning_effort", None)
            logger.warning(
                "reasoning_effort=%r rejeté par le modèle %s — rejeu sans le "
                "champ (défaut du fournisseur)",
                sent_value,
                model,
            )
        else:
            body["reasoning_effort"] = new_value
            logger.warning(
                "reasoning_effort=%r rejeté par le modèle %s — rejeu avec la "
                "valeur nommée par le 400 : %r",
                sent_value,
                model,
                new_value,
            )
        retry_request = self._with_body(request, body)
        return await self._wrapped_transport.handle_async_request(retry_request)

    @staticmethod
    def _rejection_text(exc: httpx.HTTPStatusError) -> str:
        """Le corps du 400 tel que mesuré — le message de l'exception ne
        porte que ses 500 premiers caractères, la liste des valeurs admises
        peut vivre plus loin."""
        try:
            return exc.response.text or str(exc)
        except httpx.ResponseNotRead:
            return str(exc)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body: Optional[Dict[str, Any]] = None
        sent_effort: Optional[str] = None
        caller_set_effort = False
        if request.method == "POST" and "chat/completions" in request.url.path:
            content_bytes = await request.aread()
            try:
                parsed = json.loads(content_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = None
            if isinstance(parsed, dict):
                body = parsed
                # Provenance notée AVANT l'injection (#2840) : seul un champ
                # que l'appelant n'a PAS exprimé peut être corrigé au rejeu.
                caller_set_effort = "reasoning_effort" in body
                sent_effort = body.get("reasoning_effort")
                if body.get("tools") and sent_effort is None:
                    from argumentation_analysis.core.llm_service import (
                        is_reasoning_model,
                    )

                    if is_reasoning_model(str(body.get("model", ""))):
                        body["reasoning_effort"] = "none"
                        sent_effort = "none"
                        self._with_body(request, body)
        try:
            response = await self._wrapped_transport.handle_async_request(request)
        except httpx.HTTPStatusError as exc:
            if (
                exc.response.status_code == 400
                and body is not None
                and not caller_set_effort
            ):
                retry, new_value = self._effort_retry_value(
                    self._rejection_text(exc), sent_effort
                )
                if retry:
                    return await self._retry_adapted(
                        request, body, sent_effort, new_value
                    )
            raise
        if response.status_code == 400 and body is not None and not caller_set_effort:
            await response.aread()
            retry, new_value = self._effort_retry_value(response.text, sent_effort)
            if retry:
                return await self._retry_adapted(request, body, sent_effort, new_value)
        return response

    async def aclose(self) -> None:
        await self._wrapped_transport.aclose()


# --- #3447 — le disjoncteur piloté depuis la coroutine, sans tornado -------
#
# ``CircuitBreaker.call_async`` (pybreaker 1.4.1) est construit sur
# ``tornado.gen.coroutine`` : tornado n'est déclaré ni dans
# ``environment.yml`` ni dans ``pyproject.toml``, et ``pybreaker.gen`` vaut
# ``None`` quand le module manque — le chemin chaud du transport asynchrone
# reposait donc sur un paquet non installé. Le même ``call_async`` garde
# ``self._lock`` (un ``threading.RLock``) PENDANT toute la requête HTTP : les
# appels simultanés de plusieurs boucles ou threads se sérialisent sur la
# latence du premier.
#
# La coroutine ne traverse donc plus pybreaker : c'est son automate d'état qui
# est piloté AUTOUR de l'``await``, avec ses propres primitives — la porte
# d'entrée de l'état ouvert, puis ``_handle_error`` / ``_handle_success``
# pour la comptabilité (ce que ``CircuitBreakerState.call`` fait lui-même).
# Le verrou n'est pris que pour ces deux gestes, jamais pendant l'attente
# réseau ; les transitions (``open()``, ``half_open()``, ``close()``) le
# prennent de l'intérieur.
#
# Dépendance assumée : ces trois noms sont privés chez pybreaker. Une montée
# de version les ferait disparaître bruyamment (``AttributeError`` à chaque
# requête) ; ``test_breaker_without_tornado_3447.py`` vérifie en plus leur
# présence, pour que le rouge arrive sur le bump et pas en production.
_T = TypeVar("_T")


async def _call_through_breaker(func: Callable[[], Awaitable[_T]]) -> _T:
    """Exécute ``func`` sous ``network_breaker`` sans tornado (#3447).

    Même sémantique que ``CircuitBreakerState.call_async`` : l'état est
    figé avant l'appel, l'issue est comptée sur cet état, et un déclenchement
    lève ``CircuitBreakerError`` au lieu de l'exception d'origine quand
    ``throw_new_error_on_trip`` est armé (le défaut). L'état étant figé, un
    succès tardif ne referme pas un disjoncteur qu'un appel concurrent aurait
    ouvert entre-temps — et ``call_async`` ne l'empêchait pas davantage : son
    ``RLock`` est réentrant pour le thread qui le détient, donc deux
    coroutines de la MÊME boucle le traversent déjà en parallèle. Il ne
    bloquait que les autres threads, et pendant toute la requête.
    """
    with network_breaker._lock:
        state: CBStateType = network_breaker.state
        if isinstance(state, CircuitOpenState):
            # La porte de ``CircuitOpenState.before_call``, sans sa
            # délégation synchrone : celle-ci appellerait ``func`` comme une
            # fonction ordinaire, recevrait la coroutine en valeur de retour
            # et compterait un succès qui n'a pas eu lieu.
            timeout = timedelta(seconds=network_breaker.reset_timeout)
            opened_at = network_breaker._state_storage.opened_at
            if opened_at and datetime.now(timezone.utc) < opened_at + timeout:
                raise CircuitBreakerError(
                    "Timeout not elapsed yet, circuit breaker still open"
                )
            network_breaker.half_open()
            state = network_breaker.state

    try:
        result = await func()
    except BaseException as exc:
        with network_breaker._lock:
            # ``_handle_error`` relance l'exception lui-même (ou le
            # ``CircuitBreakerError`` du déclenchement).
            state._handle_error(exc)
        raise  # inatteignable : garde le typage de sortie honnête
    with network_breaker._lock:
        state._handle_success()
    return result


class ResilientAsyncTransport(httpx.AsyncBaseTransport):
    """
    Transport httpx qui intègre Tenacity et PyBreaker pour la résilience.

    #3435 — les décorateurs ne sont PLUS empilés : ``@network_breaker``
    (pybreaker 1.4.1) enveloppe une def async en un callable SYNC, ce qui
    cache la coroutine à la détection async de tenacity — le « rejeu » que
    le client promettait était mesuré INERTE (une ``ReadTimeout`` levée une
    fois s'échappait sans second appel : sonde 05/11, ``calls: 1``). Le
    disjoncteur est piloté À L'INTÉRIEUR de la méthode décorée tenacity, pour
    que les deux étages voient réellement l'exception : le rejeu rejoue, le
    disjoncteur compte.

    #3447 — et il est piloté par ``_call_through_breaker`` (l'automate de
    pybreaker autour de l'``await``), pas par ``call_async`` : plus de
    tornado sur le chemin chaud, et plus de verrou tenu pendant la requête.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport):
        self.transport = transport

    @async_retry_on_network_error
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """
        Gère une requête asynchrone avec résilience (rejeu et disjoncteur).
        Le rejeu vit dans le décorateur tenacity (async-aware) ; le
        disjoncteur via ``_call_through_breaker`` dans le corps — voir les
        docstrings de la classe et de l'aide pour pourquoi ni l'empilement de
        décorateurs (#3435) ni ``call_async`` (#3447) ne convenaient.
        """
        logger.debug(f"Via Resilient Transport: {request.method} {request.url}")

        # L'appel est simplement transmis au transporteur suivant.
        # L'inspection de la réponse et la levée d'exception sont gérées
        # plus haut dans la chaîne (dans LoggingHttpTransport) pour garantir
        # que `raise_for_status()` est appelé sur un objet réponse valide.
        async def _inner() -> httpx.Response:
            return await self.transport.handle_async_request(request)

        return await _call_through_breaker(_inner)


def get_resilient_async_client() -> httpx.AsyncClient:
    """
    Retourne un client httpx.AsyncClient configuré avec un transport résilient
    et un logging détaillé.
    """
    base_transport = httpx.AsyncHTTPTransport()
    # #3435 — la borne par tentative vit SOUS la couche résiliente : tenacity
    # ré-invoque ce transport à chaque rejeu, donc la borne s'applique par
    # tentative et l'ensemble (tentative + attente + rejeu) tient dans le
    # budget de phase publié par l'exécuteur.
    budget_clamped = PhaseBudgetTransport(base_transport)
    resilient_transport = ResilientAsyncTransport(budget_clamped)
    # Le logger utilisé ici est celui du module network_utils
    logged_transport = LoggingHttpTransport(
        logger, wrapped_transport=resilient_transport
    )
    # #2324 : l'injection reasoning_effort est la couche la plus EXTERNE —
    # le log de la requête montre alors exactement le corps parti sur le fil
    # (avec le champ injecté), pas un corps que l'API n'a jamais vu.
    final_transport = ReasoningEffortTransport(logged_transport)

    return httpx.AsyncClient(
        transport=final_transport, timeout=settings.network.default_timeout
    )


def build_async_openai_client(**client_kwargs: Any) -> Any:
    """Le seul constructeur d'``AsyncOpenAI`` hors ``create_llm_service`` (#2391).

    #2387 a réparé le 400 ``reasoning_effort`` dans ``ReasoningEffortTransport``,
    mais un transport n'atteint que les clients construits avec lui : seul
    ``create_llm_service`` le faisait. Dix-huit sites construisaient un
    ``AsyncOpenAI`` nu et contournaient la réparation, dont la fixture du garde
    de #2322, qui restait rouge sur la route par défaut alors que la production
    était réparée (mesuré : run ``35783217532``). Poser le transport site par
    site ne tiendrait pas : le prochain client nu le contournerait de nouveau.
    Chaque construction passe donc par ici, et
    ``test_one_openai_client_constructor_2391.py`` refuse toute construction nue.

    Le transport est posé seul, sans la couche résiliente (retry, disjoncteur
    partagé) de ``get_resilient_async_client`` : ces sites n'en avaient pas, et
    un disjoncteur commun à tous les clients changerait leur comportement en
    panne. L'injection reste conditionnelle (POST ``/chat/completions`` +
    ``tools`` + famille reasoning + champ absent) : un modèle non-reasoning ou
    un appel sans outils part inchangé.
    """
    from openai import AsyncOpenAI

    if "http_client" in client_kwargs:
        raise TypeError(
            "build_async_openai_client pose lui-même http_client (#2391) : "
            "un client fourni contournerait ReasoningEffortTransport"
        )
    http_client = httpx.AsyncClient(
        transport=ReasoningEffortTransport(httpx.AsyncHTTPTransport())
    )
    return AsyncOpenAI(http_client=http_client, **client_kwargs)


if __name__ == "__main__":
    # Section de test simple pour la fonction download_file
    # Configure le logging basic pour voir les messages d'information et d'erreur
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Test 1: Téléchargement réussi d'un petit fichier ---
    # test_url_small = "https://raw.githubusercontent.com/psf/requests/main/README.md"
    # test_dest_path_small = Path("_test_downloaded_readme.md")
    # # Pour obtenir la taille attendue, on peut télécharger une fois et vérifier, ou utiliser un outil.
    # # Par exemple, `curl -sI https://raw.githubusercontent.com/psf/requests/main/README.md | grep -i content-length`
    # # Pour cet exemple, nous allons la laisser à None pour ne pas faire échouer le test si elle change.
    # test_expected_size_small = None

    # logger.info(f"--- Test 1: Téléchargement de {test_url_small} ---")
    # success_small = download_file(test_url_small, test_dest_path_small, test_expected_size_small)
    # if success_small:
    #     logger.info(f"Test 1 réussi. Fichier sauvegardé à {test_dest_path_small} (Taille: {test_dest_path_small.stat().st_size})")
    #     # os.remove(test_dest_path_small) # Nettoyer après le test
    #     # logger.info(f"Fichier de test {test_dest_path_small} supprimé.")
    # else:
    #     logger.error("Test 1 (petit fichier) échoué.")

    # --- Test 2: URL invalide ---
    # logger.info(f"--- Test 2: Téléchargement avec URL invalide ---")
    # invalid_url = "http://invalid.url.thisdoesnotexist/nonexistentfile.zip"
    # invalid_dest_path = Path("_test_invalid_download.zip")
    # success_invalid = download_file(invalid_url, invalid_dest_path)
    # if not success_invalid:
    #     logger.info("Test 2 (URL invalide) a correctement échoué.")
    #     if invalid_dest_path.exists():
    #         logger.error(f"ERREUR: Le fichier {invalid_dest_path} ne devrait pas exister après un échec de téléchargement.")
    #         # os.remove(invalid_dest_path)
    # else:
    #     logger.error("Test 2 (URL invalide) n'a pas échoué comme attendu.")

    # --- Test 3: Taille de fichier incorrecte ---
    # test_url_size_check = "https://raw.githubusercontent.com/psf/requests/main/README.md" # Même URL que test 1
    # test_dest_path_size_check = Path("_test_downloaded_readme_size_check.md")
    # incorrect_expected_size = 10 # Taille manifestement incorrecte

    # logger.info(f"--- Test 3: Vérification de taille incorrecte pour {test_url_size_check} ---")
    # success_size_check = download_file(test_url_size_check, test_dest_path_size_check, incorrect_expected_size)
    # if not success_size_check:
    #     logger.info(f"Test 3 (taille incorrecte) a correctement échoué. Fichier à {test_dest_path_size_check} (Taille: {test_dest_path_size_check.stat().st_size if test_dest_path_size_check.exists() else 'N/A'})")
    #     # if test_dest_path_size_check.exists():
    #         # os.remove(test_dest_path_size_check)
    #         # logger.info(f"Fichier de test {test_dest_path_size_check} supprimé.")
    # else:
    #     logger.error("Test 3 (taille incorrecte) n'a pas échoué comme attendu.")
    #     # if test_dest_path_size_check.exists():
    #         # os.remove(test_dest_path_size_check)

    # --- Test 4: Pas de permission d'écriture (plus difficile à simuler de manière portable) ---
    # Pourrait être testé en essayant d'écrire dans un répertoire protégé.
    # logger.info(f"--- Test 4: Tentative d'écriture dans un répertoire sans permission (simulé) ---")
    # no_permission_path = Path("/root/_test_no_permission.txt") # Unix-like, échouera probablement
    # if os.name == 'nt': # Windows
    #     no_permission_path = Path("C:/Windows/System32/config/_test_no_permission.txt") # Devrait échouer

    # success_permission = download_file(test_url_small, no_permission_path)
    # if not success_permission:
    #     logger.info(f"Test 4 (pas de permission) a correctement échoué.")
    # else:
    #     logger.error(f"Test 4 (pas de permission) n'a pas échoué comme attendu. Fichier créé à {no_permission_path} ?")

    logger.info("Tous les tests (commentés) de network_utils sont terminés.")
    pass  # Les tests sont commentés pour éviter exécution automatique et dépendances externes non garanties
