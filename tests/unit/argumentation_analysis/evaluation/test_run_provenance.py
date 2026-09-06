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
    def test_reads_env_or_none(self, monkeypatch):
        monkeypatch.delenv("OPENAI_CHAT_MODEL_ID", raising=False)
        assert chat_model_id() is None
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "test-model")
        assert chat_model_id() == "test-model"


class TestProvenanceBlock:
    def test_carries_run_identity(self, monkeypatch):
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "test-model")
        block = provenance_block(params={"workflow": "spectacular"})
        assert set(block) == {"run_started_utc", "code_sha", "chat_model_id", "params"}
        assert block["chat_model_id"] == "test-model"
        assert block["params"] == {"workflow": "spectacular"}

    def test_params_omitted_when_absent(self):
        assert "params" not in provenance_block()


class TestFileSha256:
    def test_stable_digest(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_bytes(b"payload")
        assert file_sha256(p) == hashlib.sha256(b"payload").hexdigest()
