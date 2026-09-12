"""Gardes du comparateur .env / .env.example.

Le contrôle qui compte est le NÉGATIF : une valeur légitimement identique au
canon (`GLOBAL_LLM_SERVICE=OpenAI`) ne doit pas ressortir. Sans lui, le
détecteur rend ~8 faux positifs sur 10 et la flotte apprend à l'ignorer.
"""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "check_env_completeness",
    Path(__file__).resolve().parents[4] / "scripts/security/check_env_completeness.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


CANON = (
    'GLOBAL_LLM_SERVICE="OpenAI"\n'
    'AZURE_OPENAI_API_KEY="your-azure-api-key"\n'
    '# OPTIONAL_KEY="change-me"\n'
    'REQUIRED_KEY="sk-..."\n'
)


def write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def verdicts(tmp_path: Path, env_body: str, canon: str = CANON) -> list[str]:
    env = write(tmp_path, ".env", env_body)
    ref = write(tmp_path, ".env.example", canon)
    findings, _opt, _, _ = mod.audit(env, ref)
    return findings


def test_specimen_value_is_flagged(tmp_path):
    """Contrôle positif : la valeur d'exemple laissée en place est vue."""
    out = verdicts(tmp_path, 'AZURE_OPENAI_API_KEY="your-azure-api-key"\n')
    assert any(v.startswith("SPECIMEN  AZURE_OPENAI_API_KEY") for v in out)


def test_legit_value_equal_to_canon_is_not_flagged(tmp_path):
    """Contrôle négatif : égal au canon mais de forme réelle => silence.

    C'est la garde anti-bruit. Si elle tombe, le détecteur redevient
    inutilisable même en restant « vert » sur le contrôle positif.
    """
    out = verdicts(tmp_path, 'GLOBAL_LLM_SERVICE="OpenAI"\n')
    assert not any("GLOBAL_LLM_SERVICE" in v for v in out)


def test_missing_and_empty_are_distinguished(tmp_path):
    out = verdicts(tmp_path, 'GLOBAL_LLM_SERVICE=""\n')
    assert any(v == "VIDE      GLOBAL_LLM_SERVICE" for v in out)
    assert any(v == "ABSENTE   REQUIRED_KEY" for v in out)


def test_commented_canon_entry_is_optional_not_blocking(tmp_path):
    """Une option documentee en commentaire ne doit PAS bloquer.

    Controle anti-bruit : sans cette distinction l'outil reclame a chaque
    siege les surcharges facultatives, et la flotte cesse de le lire.
    """
    env = write(tmp_path, ".env", 'GLOBAL_LLM_SERVICE="OpenAI"\n')
    ref = write(tmp_path, ".env.example", CANON)
    findings, optional, _, _ = mod.audit(env, ref)
    assert not any("OPTIONAL_KEY" in v for v in findings)
    assert any("OPTIONAL_KEY" in v for v in optional)
    assert any(v == "ABSENTE   REQUIRED_KEY" for v in findings)


def test_crlf_canon_does_not_break_comparison(tmp_path):
    """Le canon du dépôt est en CRLF : le \r ne doit pas casser l'égalité."""
    out = verdicts(
        tmp_path,
        'AZURE_OPENAI_API_KEY="your-azure-api-key"\n',
        canon=CANON.replace("\n", "\r\n"),
    )
    assert any(v.startswith("SPECIMEN  AZURE_OPENAI_API_KEY") for v in out)


def test_no_value_ever_appears_in_output(tmp_path):
    """Aucune sortie ne doit contenir une valeur, inventaire compris."""
    env = write(tmp_path, ".env", 'REQUIRED_KEY="sk-valeur-tres-secrete-0123"\n')
    ref = write(tmp_path, ".env.example", CANON)
    findings, _opt, _, inventory = mod.audit(env, ref)
    blob = "\n".join(findings + inventory)
    assert "sk-valeur-tres-secrete-0123" not in blob
    assert "REQUIRED_KEY" in blob


@pytest.mark.parametrize("shape", ["your-x", "votre_x", "change-me", "a_remplir"])
def test_specimen_shapes(tmp_path, shape):
    canon = f'K="{shape}"\n'
    out = verdicts(tmp_path, f'K="{shape}"\n', canon=canon)
    assert any(v.startswith("SPECIMEN  K") for v in out)
