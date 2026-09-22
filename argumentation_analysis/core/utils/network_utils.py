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
from pathlib import Path
import requests
import httpx
from typing import Optional, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from pybreaker import CircuitBreaker, CircuitBreakerError

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
    """#2324 — le paramètre que le connecteur SK ne peut pas exprimer.

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
    """

    def __init__(self, wrapped_transport: httpx.AsyncBaseTransport):
        self._wrapped_transport = wrapped_transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "chat/completions" in request.url.path:
            content_bytes = await request.aread()
            try:
                body = json.loads(content_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = None
            if (
                isinstance(body, dict)
                and body.get("tools")
                and "reasoning_effort" not in body
            ):
                from argumentation_analysis.core.llm_service import is_reasoning_model

                if is_reasoning_model(str(body.get("model", ""))):
                    body["reasoning_effort"] = "none"
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
                    request.stream = httpx.Request(
                        "POST", request.url, content=new_content
                    ).stream
                    request._content = new_content
                    request.headers["content-length"] = str(len(new_content))
        return await self._wrapped_transport.handle_async_request(request)

    async def aclose(self) -> None:
        await self._wrapped_transport.aclose()


class ResilientAsyncTransport(httpx.AsyncBaseTransport):
    """
    Transport httpx qui intègre Tenacity et PyBreaker pour la résilience.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport):
        self.transport = transport

    @async_retry_on_network_error
    @network_breaker
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """
        Gère une requête asynchrone avec résilience (rejeu et disjoncteur).
        Les exceptions sont gérées par les décorateurs Tenacity et PyBreaker.
        """
        logger.debug(f"Via Resilient Transport: {request.method} {request.url}")
        # L'appel est simplement transmis au transporteur suivant.
        # L'inspection de la réponse et la levée d'exception sont gérées
        # plus haut dans la chaîne (dans LoggingHttpTransport) pour garantir
        # que `raise_for_status()` est appelé sur un objet réponse valide.
        response = await self.transport.handle_async_request(request)
        return response


def get_resilient_async_client() -> httpx.AsyncClient:
    """
    Retourne un client httpx.AsyncClient configuré avec un transport résilient
    et un logging détaillé.
    """
    base_transport = httpx.AsyncHTTPTransport()
    resilient_transport = ResilientAsyncTransport(base_transport)
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
