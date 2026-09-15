"""Born-red guard for the withdrawal of the two dead provider functions (#2116 A2).

``invoke_dung_student`` and ``register_dung_student_provider`` had zero
production callers (measured — the live access path instantiates
``DungStudentProvider`` directly in ``orchestration/invoke_callables.py``).
They are withdrawn; the class itself stays (it is alive and tested).
"""

import argumentation_analysis.adapters.dung_student_provider as provider_module


def test_invoke_dung_student_is_withdrawn():
    assert not hasattr(provider_module, "invoke_dung_student"), (
        "invoke_dung_student was withdrawn (#2116 A2): 0 production callers, "
        "the live path instantiates DungStudentProvider directly"
    )


def test_register_dung_student_provider_is_withdrawn():
    assert not hasattr(provider_module, "register_dung_student_provider"), (
        "register_dung_student_provider was withdrawn (#2116 A2): 0 production "
        "callers, the registry path was never wired"
    )


def test_the_provider_class_survives():
    """Control: the withdrawal is scoped to the two functions — the class stays."""
    assert hasattr(provider_module, "DungStudentProvider")
