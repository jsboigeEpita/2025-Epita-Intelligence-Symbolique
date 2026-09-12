"""Gardes du comparateur .env / .env.example.

Le contrôle qui compte est le NÉGATIF : une valeur légitimement identique au
canon (`GLOBAL_LLM_SERVICE=OpenAI`) ne doit pas ressortir. Sans lui, le
détecteur rend ~8 faux positifs sur 10 et la flotte apprend à l'ignorer.
"""

import importlib.util
import sys
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


def run_main(tmp_path, env_body, canon_body):
    """Le garde du canon vacuous vit dans main(), pas dans audit().

    Un test qui passerait par `verdicts` ne le traverserait jamais : il
    mesurerait audit() et certifierait main(). D'ou l'argv.
    """
    env = write(tmp_path, ".env", env_body)
    ref = write(tmp_path, "canon", canon_body)
    argv = ["check_env_completeness.py", "--env", str(env), "--canon", str(ref)]
    old, sys.argv = sys.argv, argv
    try:
        return mod.main()
    finally:
        sys.argv = old


LEGIT_ENV = (
    'GLOBAL_LLM_SERVICE="OpenAI"\n'
    'AZURE_OPENAI_API_KEY="vraie"\n'
    'REQUIRED_KEY="sk-vraie"\n'
)

COMMENTS_ONLY = "# RIEN=1\n\n# QUE DES COMMENTAIRES\n"


def test_real_canon_still_returns_complet(tmp_path, capsys):
    """CONTROLE POSITIF du garde : un garde qui refuserait TOUT canon ferait
    passer les deux cas vacuous ci-dessous sans rien mesurer."""
    assert run_main(tmp_path, LEGIT_ENV, CANON) == 0
    assert "complet" in capsys.readouterr().out


@pytest.mark.parametrize(
    "canon, forme",
    [("", "vide"), (COMMENTS_ONLY, "commentaires seuls")],
)
def test_vacuous_canon_is_refused_not_green(tmp_path, capsys, canon, forme):
    """Un canon sans aucune cle requise rendait `complet` exit 0.

    Mesure d'origine : un `git show <ref>:<path>` mange par MSYS a produit un
    canon vide par redirection, et l'outil a certifie « complet » un siege
    incomplet. Zero exigence n'est pas une conformite — et ce vert-la est pire
    qu'un rouge : il AUTORISE le geste suivant.
    """
    assert run_main(tmp_path, LEGIT_ENV, canon) == 2, forme
    out = capsys.readouterr()
    assert "canon inutilisable" in out.err
    assert "complet" not in out.out
