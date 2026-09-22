"""#2383 — un diagnostic ne verdit pas sur une configuration inexistante.

`scripts/validation/test_environment_simple.py` lisait ``OPENAI_CHAT_MODEL_ID``
pour **construire** un ``OpenAIChatCompletion``, avec un repli codé en dur
``"gpt-5.6-luna"`` : variable absente, le kernel était bâti sur ce défaut et le
script rendait « ✅ Kernel créé avec succès » pour une configuration qui n'était
pas dans ``.env``. Même racine que #2377 — un défaut codé en dur fait passer un
contrôle sur un objet qui n'est pas celui de production. L'entrée a été versée
à la famille par la revue coord R1043 ; le contraste est
``validation_environnement_simple.py``, diagnostic pur (il asserte ce qu'il
trouve), volontairement hors périmètre.

Le contrat réparé : variable absente **ou vide** ⇒ « ❌ non configurée » et
refus — le vocabulaire du contrôle de clé API qui précède ; variable présente ⇒
le kernel est bâti sur la valeur **lue**, et la sortie **nomme** cette valeur.
Pas de délégation au résolveur : lire la configuration EST le test, le fichier
reste class D au recensement gelé #2352 pour cette raison exacte.

Le siège « ``.env`` ne fournit pas le modèle » est imposé **dans le module** :
``load_dotenv`` y est neutralisé, sinon il réinjecterait ``.env`` entre le
``delenv`` du test et la lecture — un clone frais sans la variable est une
configuration réelle et documentée, pas une fabrication. Sur ``main`` d'avant
réparation, chaque test de divergence échoue **en valeur** (le verdict « ✅ »
fabriqué, le modèle non nommé, la constante présente), jamais en import : le
module visé existe des deux côtés.
"""

import ast
import asyncio
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = REPO_ROOT / "scripts" / "validation" / "test_environment_simple.py"

# Les préfixes d'un id de modèle — le motif de la constante interdite.
_MODEL_PREFIXES = ("gpt-", "openai/", "claude-", "azure/", "glm-", "qwen")


def _load_diagnostic():
    """Le module du script, chargé par chemin — ``scripts/`` n'est pas un package.

    Le chargement exécute ``import argumentation_analysis.core.environment``
    (activation de l'environnement) : coût payé **une fois** au chargement du
    présent module, pas à chaque test. Il charge ``.env`` dans ``os.environ``,
    ce qui ne gêne pas : chaque test impose son siège par ``delenv``/``setenv``.
    """
    spec = importlib.util.spec_from_file_location("seat_env_diagnostic_2383", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def diagnostic():
    return _load_diagnostic()


def _run(diagnostic, monkeypatch, seat) -> tuple:
    """Appelle ``test_environment()`` sous un siège, rend (verdict, sortie)."""
    # Le siège est imposé APRÈS le chargement (l'activation a déjà tourné) mais
    # AVANT l'appel — sans la neutralisation, ``load_dotenv()`` rappelé DANS la
    # fonction réinjecterait ``.env`` et déciderait du cas à la place du test.
    monkeypatch.setattr(diagnostic, "load_dotenv", lambda *a, **k: False)
    for var in ("OPENAI_API_KEY", "OPENAI_CHAT_MODEL_ID"):
        monkeypatch.delenv(var, raising=False)
    for var, value in seat.items():
        monkeypatch.setenv(var, value)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        verdict = asyncio.run(diagnostic.test_environment())
    return verdict, buffer.getvalue()


# ===========================================================================
# 1. La divergence — le cas non configuré
# ===========================================================================


def test_unconfigured_model_is_reported_not_substituted(diagnostic, monkeypatch):
    """Le né-rouge de #2383 : la configuration ne fournit pas le modèle.

    Avant réparation : verdict ``True`` et « ✅ Kernel créé avec succès », le
    kernel étant bâti sur le littéral — l'échec nomme le verdict fabriqué.
    """
    verdict, out = _run(
        diagnostic, monkeypatch, {"OPENAI_API_KEY": "sk-not-a-real-key"}
    )

    assert "🧪 TEST ENVIRONNEMENT" in out, f"la fonction n'a pas tourné: {out!r}"
    assert (
        verdict is False
    ), f"verdict {verdict!r} alors que le modèle n'est pas configuré — sortie: {out!r}"
    assert "OPENAI_CHAT_MODEL_ID non configurée" in out, out
    assert (
        "succès" not in out
    ), f"un succès de construction est annoncé sans configuration: {out!r}"


def test_empty_model_is_not_configured_either(diagnostic, monkeypatch):
    """Vide ≠ configuré (#2281) : un repli sur vide est le même défaut.

    Avant réparation, ``os.getenv(var, "gpt-5.6-luna")`` rendait la chaîne
    **vide** posée dans l'environnement — et construisait dessus quand même.
    """
    verdict, out = _run(
        diagnostic,
        monkeypatch,
        {"OPENAI_API_KEY": "sk-not-a-real-key", "OPENAI_CHAT_MODEL_ID": ""},
    )

    assert "🧪 TEST ENVIRONNEMENT" in out, f"la fonction n'a pas tourné: {out!r}"
    assert verdict is False, f"verdict {verdict!r} sur un modèle vide — sortie: {out!r}"
    assert "OPENAI_CHAT_MODEL_ID non configurée" in out, out
    assert "succès" not in out, out


# ===========================================================================
# 2. L'accord — le cas configuré (vert des deux côtés sur le verdict)
# ===========================================================================


def test_configured_model_builds_and_names_it(diagnostic, monkeypatch):
    """Configuré ⇒ succès, sur la valeur lue, et la sortie la NOMME.

    Le verdict ``True`` est un accord (vert avant et après) ; l'exigence de
    nommer la valeur est la partie réparée — un diagnostic dit ce qu'il a
    construit, sinon l'aval ne peut pas distinguer « configuré à X » de
    « configuré à je-ne-sais-quoi ».
    """
    verdict, out = _run(
        diagnostic,
        monkeypatch,
        {
            "OPENAI_API_KEY": "sk-not-a-real-key",
            "OPENAI_CHAT_MODEL_ID": "openai/gpt-5.6-pro",
        },
    )

    assert "🧪 TEST ENVIRONNEMENT" in out, f"la fonction n'a pas tourné: {out!r}"
    assert (
        verdict is True
    ), f"verdict {verdict!r} sur un modèle configuré — sortie: {out!r}"
    assert "succès" in out, out
    assert (
        "openai/gpt-5.6-pro" in out
    ), f"la sortie ne nomme pas le modèle construit: {out!r}"


def test_missing_api_key_still_refuses(diagnostic, monkeypatch):
    """Le contrat antérieur est intact : clé absente ⇒ refus (vert des deux côtés)."""
    verdict, out = _run(diagnostic, monkeypatch, {})

    assert "🧪 TEST ENVIRONNEMENT" in out, f"la fonction n'a pas tourné: {out!r}"
    assert verdict is False
    assert "OPENAI_API_KEY non trouvée" in out, out


# ===========================================================================
# 3. La garde — plus aucune constante de modèle dans le diagnostic
# ===========================================================================


def test_the_file_declares_no_model_constant():
    """La constante de repli ne doit pas renaître (DoD 1).

    Avant réparation, ``"gpt-5.6-luna"`` était une constante du fichier — cet
    échec est en **valeur de constante**, pas en import. La lecture de la
    variable reste (c'est le métier d'un diagnostic class D au recensement
    #2352) ; c'est la *substitution* qui est interdite. AST, pas texte : les
    commentaires peuvent nommer l'histoire du défaut, les constantes non.
    """
    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8-sig"))
    constants = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]

    hits = [c for c in constants if c.startswith(_MODEL_PREFIXES)]

    assert hits == [], f"le diagnostic porte des constantes de modèle: {hits}"
