"""JVM worker setup must not mutate the pytest caller's environment."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures import jvm_subprocess_fixture as fixture_module


@pytest.mark.parametrize("root_dotenv", [True, False])
def test_jvm_worker_uses_only_root_dotenv_without_mutating_parent(
    tmp_path, monkeypatch, root_dotenv
):
    root = tmp_path / "checkout"
    fixture_dir = root / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=foreign\nJAVA_HOME=foreign-java\n", encoding="utf-8"
    )
    if root_dotenv:
        (root / ".env").write_text(
            "OPENAI_API_KEY=root-key\nJAVA_HOME=root-java\n"
            "TWEETY_CLASSPATH=root-classpath\n",
            encoding="utf-8",
        )
    worker = root / "worker.py"
    worker.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(
        fixture_module, "__file__", str(fixture_dir / "jvm_subprocess_fixture.py")
    )
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.delenv("TWEETY_CLASSPATH", raising=False)
    seen = {}

    def capture(command, **kwargs):
        seen.update(kwargs["env"])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fixture_module.subprocess, "run", capture)
    runner = fixture_module.run_in_jvm_subprocess.__wrapped__()
    runner(worker)

    assert os.environ["OPENAI_API_KEY"] == ""
    assert "JAVA_HOME" not in os.environ
    assert "TWEETY_CLASSPATH" not in os.environ
    assert seen["OPENAI_API_KEY"] == ""
    assert seen.get("JAVA_HOME") == ("root-java" if root_dotenv else None)
    assert seen.get("TWEETY_CLASSPATH") == ("root-classpath" if root_dotenv else None)
    assert seen["PROJECT_ROOT"] == str(root)


def test_jvm_worker_preserves_explicit_empty_caller_jvm_values(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    fixture_dir = root / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    (root / ".env").write_text(
        "JAVA_HOME=root-java\nTWEETY_CLASSPATH=root-classpath\n", encoding="utf-8"
    )
    worker = root / "worker.py"
    worker.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(
        fixture_module, "__file__", str(fixture_dir / "jvm_subprocess_fixture.py")
    )
    monkeypatch.setenv("JAVA_HOME", "")
    monkeypatch.setenv("TWEETY_CLASSPATH", "")
    seen = {}

    def capture(command, **kwargs):
        seen.update(kwargs["env"])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fixture_module.subprocess, "run", capture)
    fixture_module.run_in_jvm_subprocess.__wrapped__()(worker)

    assert seen["JAVA_HOME"] == ""
    assert seen["TWEETY_CLASSPATH"] == ""
    assert os.environ["JAVA_HOME"] == ""
    assert os.environ["TWEETY_CLASSPATH"] == ""
