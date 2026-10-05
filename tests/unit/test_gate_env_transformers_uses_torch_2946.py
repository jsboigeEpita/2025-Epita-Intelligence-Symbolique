"""#2946: the env the gate installs must let transformers USE its torch.

Main's lock serves pytorch 2.2.2 with transformers 5.17.0 (unpinned in
environment.yml). transformers 5.x requires a newer torch and DISABLES the
one it finds: ``is_torch_available()`` returns False and every model class
becomes a placeholder that raises ``ImportError`` when used.
``from transformers import pipeline`` still succeeds, so every import-based
probe reports the capability as present — the failure moves to the first
call. Measured on ai-01 and po-2025 in conda-lock install envs; torch
itself loads (#2856's witness covers that layer), transformers refuses to
use it. The environment.yml note records the repair (transformers<5).

The witness runs in a FRESH SUBPROCESS: the session conftest imports
torch/transformers before jpype, and transformers caches its backend
decision at import, so an in-process check would test the session's cache,
not the env. No network: the model is built from a config alone, no
weights are downloaded.
"""

import subprocess
import sys

# Answers the real question — "can transformers construct a model in THIS
# env?" — not "is the package importable?". The from_config build never
# touches the network.
_PROBE = (
    "from transformers.utils import is_torch_available\n"
    "assert is_torch_available(), (\n"
    "    'transformers disabled torch in this env (#2946): the lock serves "
    "a torch older than the transformers line requires'\n"
    ")\n"
    "from transformers import AutoModelForSequenceClassification, BertConfig\n"
    "cfg = BertConfig(hidden_size=8, num_hidden_layers=1, "
    "num_attention_heads=1, intermediate_size=16, num_labels=2, vocab_size=100)\n"
    "model = AutoModelForSequenceClassification.from_config(cfg)\n"
    "print('BUILT', type(model).__name__)\n"
)


def test_the_gate_envs_transformers_uses_torch():
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (
        "transformers cannot build a model in this env (#2946):\n"
        f"stdout: {proc.stdout[-400:]}\nstderr: {proc.stderr[-800:]}"
    )
    assert "BUILT" in proc.stdout, proc.stdout
