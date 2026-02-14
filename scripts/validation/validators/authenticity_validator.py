import argumentation_analysis.core.environment

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validator for system component authenticity.
"""

import os
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Tuple

# Ajout du chemin pour les imports si nécessaire (dépend de la structure finale)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# sys.path.insert(0, str(PROJECT_ROOT)) # Décommenter si les imports relatifs ne fonctionnent pas

# Tentative d'import des composants nécessaires
try:
    from config.unified_config import UnifiedConfig
except ImportError:
    # Gérer le cas où UnifiedConfig n'est pas accessible directement
    # Cela peut nécessiter un ajustement des imports ou de la structure
    UnifiedConfig = None
    logging.warning("UnifiedConfig not found, authenticity checks might be limited.")

logger = logging.getLogger(__name__)


async def validate_authenticity(
    report_errors_list: list, available_components: Dict[str, bool]
) -> Dict[str, Any]:
    """Validates the authenticity of system components."""
    logger.info("🔍 Validation de l'authenticité des composants...")

    authenticity_results = {
        "llm_service": {"status": "unknown", "details": {}},
        "tweety_service": {"status": "unknown", "details": {}},
        "taxonomy": {"status": "unknown", "details": {}},
        "configuration": {"status": "unknown", "details": {}},
        "summary": {},
    }

    try:
        # Validation du service LLM
        if UnifiedConfig and available_components.get("unified_config", False):
            config = UnifiedConfig()

            llm_valid, llm_details = await _validate_llm_service_authenticity(config)
            authenticity_results["llm_service"] = {
                "status": "authentic" if llm_valid else "mock_or_invalid",
                "details": llm_details,
            }

            # Validation du service Tweety
            tweety_valid, tweety_details = _validate_tweety_service_authenticity(config)
            authenticity_results["tweety_service"] = {
                "status": "authentic" if tweety_valid else "mock_or_invalid",
                "details": tweety_details,
            }

            # Validation de la taxonomie
            taxonomy_valid, taxonomy_details = _validate_taxonomy_authenticity(config)
            authenticity_results["taxonomy"] = {
                "status": "authentic" if taxonomy_valid else "mock_or_invalid",
                "details": taxonomy_details,
            }

            # Validation de la cohérence de configuration
            config_valid, config_details = _validate_configuration_coherence(config)
            authenticity_results["configuration"] = {
                "status": "coherent" if config_valid else "incoherent",
                "details": config_details,
            }
        else:
            authenticity_results["error"] = (
                "Configuration unifiée non disponible ou UnifiedConfig non importé"
            )
            logger.warning(
                "UnifiedConfig non disponible pour la validation d'authenticité."
            )

    except Exception as e:
        authenticity_results["error"] = str(e)
        report_errors_list.append(
            {
                "context": "authenticity_validation",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
        )

    return authenticity_results


async def _validate_llm_service_authenticity(config) -> Tuple[bool, Dict[str, Any]]:
    """Valide l'authenticité du service LLM."""
    details = {
        "component": "llm_service",
        "required_authentic": getattr(config, "require_real_gpt", False),
        "api_key_present": bool(os.getenv("OPENAI_API_KEY")),
        "mock_level": getattr(config, "mock_level", "unknown"),
    }

    if not getattr(config, "require_real_gpt", False):
        details["status"] = "mock_allowed"
        return True, details

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        details["status"] = "missing_api_key"
        details["error"] = "Clé API OpenAI manquante"
        return False, details

    if not api_key.startswith(("sk-", "sk-proj-")):
        details["status"] = "invalid_api_key"
        details["error"] = "Format de clé API invalide"
        return False, details

    details["status"] = "authentic"
    details["api_key_format_valid"] = True
    return True, details


def _validate_tweety_service_authenticity(config) -> Tuple[bool, Dict[str, Any]]:
    """Valide l'authenticité du service Tweety."""
    details = {
        "component": "tweety_service",
        "required_authentic": getattr(config, "require_real_tweety", False),
        "jvm_enabled": getattr(config, "enable_jvm", False),
        "use_real_jpype": os.getenv("USE_REAL_JPYPE", "").lower() == "true",
    }

    if not getattr(config, "require_real_tweety", False):
        details["status"] = "mock_allowed"
        return True, details

    if not getattr(config, "enable_jvm", False):
        details["status"] = "jvm_disabled"
        details["error"] = "JVM désactivée mais Tweety réel requis"
        return False, details

    if not details["use_real_jpype"]:
        details["status"] = "jpype_mock"
        details["error"] = "USE_REAL_JPYPE non défini ou false"
        return False, details

    jar_paths = [
        PROJECT_ROOT / "libs" / "tweety-full.jar",
        PROJECT_ROOT / "libs" / "tweety.jar",
        PROJECT_ROOT / "portable_jdk" / "tweety-full.jar",
    ]

    jar_found = False
    for jar_path in jar_paths:
        if jar_path.exists():
            details["jar_path"] = str(jar_path)
            details["jar_size"] = jar_path.stat().st_size
            jar_found = True
            break

    if not jar_found:
        details["status"] = "jar_missing"
        details["error"] = "JAR Tweety non trouvé"
        details["searched_paths"] = [str(p) for p in jar_paths]
        return False, details

    if details.get("jar_size", 0) < 1000000:  # 1MB minimum
        details["status"] = "jar_too_small"
        details["error"] = f"JAR trop petit ({details.get('jar_size', 0)} bytes)"
        return False, details

    details["status"] = "authentic"
    return True, details


def _validate_taxonomy_authenticity(config) -> Tuple[bool, Dict[str, Any]]:
    """Valide l'authenticité de la taxonomie."""
    details = {
        "component": "taxonomy",
        "required_full": getattr(config, "require_full_taxonomy", False),
        "taxonomy_size": getattr(config, "taxonomy_size", "unknown"),
    }

    if not getattr(config, "require_full_taxonomy", False):
        details["status"] = "mock_allowed"
        return True, details

    taxonomy_size = str(getattr(config, "taxonomy_size", "")).upper()
    if taxonomy_size != "FULL":
        details["status"] = "size_not_full"
        details["error"] = f"Taille taxonomie: {taxonomy_size}, requis: FULL"
        return False, details

    try:
        taxonomy_config = (
            config.get_taxonomy_config()
            if hasattr(config, "get_taxonomy_config")
            else {}
        )
        expected_nodes = taxonomy_config.get("node_count", 0)

        if expected_nodes < 1000:
            details["status"] = "insufficient_nodes"
            details["error"] = (
                f"Nombre de nœuds insuffisant: {expected_nodes}, requis: >=1000"
            )
            return False, details

        details["expected_nodes"] = expected_nodes
    except Exception as e:
        details["taxonomy_config_error"] = str(e)

    details["status"] = "authentic"
    return True, details


def _validate_configuration_coherence(config) -> Tuple[bool, Dict[str, Any]]:
    """Valide la cohérence de la configuration."""
    details = {
        "component": "configuration",
        "mock_level": getattr(config, "mock_level", "unknown"),
    }

    coherence_issues = []

    require_real_gpt = getattr(config, "require_real_gpt", False)
    mock_level = str(getattr(config, "mock_level", "")).upper()

    if require_real_gpt and mock_level in ["FULL", "COMPLETE"]:
        coherence_issues.append("require_real_gpt=True mais mock_level=FULL/COMPLETE")

    require_real_tweety = getattr(config, "require_real_tweety", False)
    enable_jvm = getattr(config, "enable_jvm", False)

    if require_real_tweety and not enable_jvm:
        coherence_issues.append("require_real_tweety=True mais enable_jvm=False")

    require_full_taxonomy = getattr(config, "require_full_taxonomy", False)
    taxonomy_size = str(getattr(config, "taxonomy_size", "")).upper()

    if require_full_taxonomy and taxonomy_size != "FULL":
        coherence_issues.append(
            f"require_full_taxonomy=True mais taxonomy_size={taxonomy_size}"
        )

    if coherence_issues:
        details["status"] = "incoherent"
        details["issues"] = coherence_issues
        return False, details

    details["status"] = "coherent"
    return True, details
