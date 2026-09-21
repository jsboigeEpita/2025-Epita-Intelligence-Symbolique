"""Tests for argumentation_analysis/evaluation/run_provenance.py (#2045).

Le bloc de provenance relie un dump d'état à son run : horodatage, SHA de
code, modèle, paramètres. Ces tests verrouillent le contrat du bloc.
"""

import hashlib
from datetime import datetime

from argumentation_analysis.evaluation.run_provenance import (
    chat_model_id,
    code_sha,
    file_sha256,
    now_utc_iso,
    provenance_block,
)

# Chaque test possède TOUTES les variables de route (#2352) : le label rend le
# modèle résolu, un .env hérité ne doit pas décider du cas.
_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
)


class TestNowUtcIso:
    def test_parses_as_utc_iso(self):
        parsed = datetime.fromisoformat(now_utc_iso())
        assert parsed.tzinfo is not None
        assert parsed.utcoffset().total_seconds() == 0


class TestCodeSha:
    def test_sha_in_git_checkout(self):
        # L'arbre de test EST un checkout git → SHA calculable, hexadécimal court.
        sha = code_sha()
        assert sha is not None
        assert len(sha) >= 7
        assert all(c in "0123456789abcdef" for c in sha)


class TestChatModelId:
    def test_renders_the_resolved_model_or_none(self, monkeypatch):
        # #2352/#2370 : le label rend le modèle RÉSOLU, pas la variable brute.
        # Sans clé configurée, aucun LLM ne tourne — le label reste None (le
        # défaut du résolveur serait une provenance fantôme sur l'artefact).
        for var in _ROUTE_VARS:
            monkeypatch.delenv(var, raising=False)
        assert chat_model_id() is None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-synthetic-not-a-real-key")
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "test-model")
        assert chat_model_id() == "test-model"


class TestProvenanceBlock:
    def test_carries_run_identity(self, monkeypatch):
        # Le label du bloc suit le même contrat résolu que chat_model_id :
        # clé réelle posée, sinon le bloc rendrait None en CI keyless.
        for var in _ROUTE_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-synthetic-not-a-real-key")
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "test-model")
        block = provenance_block(params={"workflow": "spectacular"})
        # Contrat #2045 + #2282 : identité de run + environnement sondé du run.
        assert set(block) == {
            "run_started_utc",
            "code_sha",
            "chat_model_id",
            "params",
            "environment",
        }
        assert block["chat_model_id"] == "test-model"
        assert block["params"] == {"workflow": "spectacular"}
        assert "jvm" in block["environment"]

    def test_params_omitted_when_absent(self):
        assert "params" not in provenance_block()


class TestFileSha256:
    def test_stable_digest(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_bytes(b"payload")
        assert file_sha256(p) == hashlib.sha256(b"payload").hexdigest()
