# -*- coding: utf-8 -*-
"""The PL belief set keeps the model's proposition order (#2829).

``text_to_belief_set`` built ``propositions`` from a ``set``, whose order moves
with PYTHONHASHSEED. ``generate_queries`` serialises that list into the
GeneratePLQueryIdeas prompt, so the same input produced a different prompt, and
a different cache key, in each process: the replay band missed the cassette its
own record job had written.
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)

ROOT = Path(__file__).resolve().parents[6]

# Enough names that a set order matching the declared one is not a coincidence.
DECLARED = [
    "zeta",
    "alpha",
    "mid",
    "beta",
    "omega",
    "gamma",
    "delta",
    "kappa",
    "sigma",
    "theta",
]


def _agent() -> PropositionalLogicAgent:
    kernel = Kernel()
    kernel.add_service(
        OpenAIChatCompletion(
            service_id="keyless_2829", ai_model_id="keyless", api_key="keyless"
        )
    )
    # The bridge is injected: the order is decided before any Tweety call, and
    # the probe below runs outside pytest's JVM.
    bridge = MagicMock()
    bridge.initializer.is_jvm_ready.return_value = True
    bridge.pl_handler.pl_check_consistency.return_value = True
    agent = PropositionalLogicAgent(
        kernel=kernel,
        agent_name="PlOrder2829",
        service_id="keyless_2829",
        tweety_bridge=bridge,
    )
    agent._invoke_llm_for_json = AsyncMock(
        side_effect=[
            ({"propositions": DECLARED + ["alpha"]}, ""),
            ({"formulas": ["zeta => alpha", "beta || omega"]}, ""),
        ]
    )
    return agent


async def test_propositions_keep_the_declared_order():
    belief_set, message = await _agent().text_to_belief_set("un texte")
    assert belief_set is not None, message
    assert belief_set.propositions == DECLARED


def test_propositions_do_not_depend_on_the_hash_seed():
    """Two processes with different hash seeds build the same list."""
    probe = (
        "import asyncio, json, sys\n"
        "sys.path[:0] = [r'%s']\n"
        "from tests.unit.argumentation_analysis.agents.core.logic."
        "test_pl_propositions_order_2829 import _agent\n"
        "bs, _ = asyncio.run(_agent().text_to_belief_set('un texte'))\n"
        "print(json.dumps(bs.propositions))\n"
    ) % str(ROOT)
    outputs = set()
    for seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        done = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert done.returncode == 0, done.stderr[-2000:]
        outputs.add(done.stdout.strip().splitlines()[-1])
    assert len(outputs) == 1, outputs
