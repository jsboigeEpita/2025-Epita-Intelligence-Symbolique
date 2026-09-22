"""#2381 — ``config/unified_config.py`` converge vers le défaut nommé du résolveur.

Ce module portait **7** déclarations du littéral ``"gpt-5.6-luna"`` (champ de
dataclass, contrainte d'authenticité, service_id, deux presets, repli d'env,
auto-assertion) — un second système de configuration parallèle à
``settings.DEFAULT_CHAT_MODEL_ID``. La plus toxique était l'auto-assertion
``validate_config`` : elle n'acceptait que la copie du littéral qu'elle venait
de comparer, un accord tautologique qui invalidait toute configuration
d'env d'un autre modèle.

Le contrat réparé : le défaut vit dans ``settings.DEFAULT_CHAT_MODEL_ID``
(référencé, pas copié), et un modèle configuré est une route valide — les
routes se résolvent, elles ne se comparent pas à un littéral.

Sur ``main`` d'avant réparation, le test structurel échoue **en valeur** (les
7 constantes sont encore là) et le test de l'auto-assertion échoue en valeurs
d'erreurs rendues.
"""

import ast
from pathlib import Path

from config.unified_config import UnifiedConfig, load_config_from_env, validate_config
from argumentation_analysis.config.settings import DEFAULT_CHAT_MODEL_ID

REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG = REPO_ROOT / "config" / "unified_config.py"

_MODEL_PREFIXES = ("gpt-", "openai/", "claude-", "azure/", "glm-", "qwen")


def test_no_model_literal_remains_in_the_config_module():
    """Les 7 déclarations ont convergé — plus aucune constante de modèle.

    AST, pas texte : les commentaires peuvent raconter l'histoire du défaut ;
    les constantes exécutables non. Avant réparation : ``['gpt-5.6-luna'] × 7``.
    """
    tree = ast.parse(_CONFIG.read_text(encoding="utf-8-sig"))
    hits = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith(_MODEL_PREFIXES)
    ]

    assert (
        hits == []
    ), f"le module de configuration porte des constantes de modèle: {hits}"


def test_the_default_is_the_named_constant_not_a_copy():
    """Le défaut référence ``settings.DEFAULT_CHAT_MODEL_ID`` (accord).

    L'égalité de valeur tenait déjà avant réparation — l'accord est le
    comportement préservé ; ce que le test structurel ci-dessus interdit,
    c'est la *copie*.
    """
    assert UnifiedConfig().default_model == DEFAULT_CHAT_MODEL_ID


def test_env_seat_still_overrides_the_default(monkeypatch):
    """La variable d'env reste l'autorité — accord des deux côtés."""
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "openai/gpt-5.6-pro")

    assert load_config_from_env().default_model == "openai/gpt-5.6-pro"


def test_validate_config_accepts_a_configured_model():
    """L'auto-assertion tautologique est morte : un modèle configuré est valide.

    Avant réparation : ``validate_config`` rendait « default_model devrait
    être 'gpt-5.6-luna' » pour tout autre modèle — y compris ceux que l'env
    venait de configurer. Un modèle est une route : les routes se résolvent.
    """
    config = UnifiedConfig()
    config.default_model = "openai/gpt-5.6-pro"

    errors = validate_config(config)

    assert not [
        error for error in errors if "default_model" in error
    ], f"le validateur épingle encore un littéral de modèle: {errors}"
