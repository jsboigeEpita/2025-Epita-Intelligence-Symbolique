import pytest
from jtms import JTMS
from atms import ATMS

strict_jtms = True

# ---------- Setup helpers ----------

@pytest.fixture
def atms():
    return ATMS()

def setup_simple_jtms():
    jtms = JTMS(strict_jtms)
    jtms.add_belief("A")
    jtms.add_belief("B")
    jtms.add_belief("C")
    return jtms

# -------------- Tests --------------

# -------------- JTMS ---------------

def test_invalid_justification_belief_not_found():
    jtms = setup_simple_jtms()
    
    with pytest.raises(KeyError):
        jtms.add_justification(["A", "Z"], [], "D")

    with pytest.raises(KeyError):
        jtms.add_justification(["A"], ["X"], "D")

def test_non_monotonic_justification():
    jtms = setup_simple_jtms()
    jtms.add_justification(["A"], ["B"], "C")

    jtms.set_belief_validity("A", True)
    jtms.set_belief_validity("B", False)

    jtms.show()

    assert jtms.beliefs["C"].valid is True

    jtms.set_belief_validity("B", True)

    assert jtms.beliefs["C"].valid is None

def test_change_propagation():
    jtms = setup_simple_jtms()
    jtms.add_belief("D")
    jtms.add_justification(["A"], [], "B")
    jtms.add_justification(["B"], [], "C")
    jtms.add_justification(["C"], [], "D")

    jtms.set_belief_validity("A", True)

    assert jtms.beliefs["D"].valid is True

    jtms.set_belief_validity("A", False)

    assert jtms.beliefs["D"].valid is None

def test_circular_justifications_handled():
    jtms = JTMS()
    jtms.add_belief("A")
    jtms.add_belief("B")
    jtms.add_justification(["B"], [], "A")
    jtms.add_justification([], ["A"], "B")

    jtms.set_belief_validity("A", True)

    assert jtms.beliefs["A"].non_monotonic is True
    assert jtms.beliefs["B"].non_monotonic is True

def test_remove_belief_with_dependents():
    jtms = setup_simple_jtms()
    jtms.add_justification(["A"], [], "C")

    jtms.set_belief_validity("A", True)
    assert jtms.beliefs["C"].valid is True

    jtms.remove_belief("A")
    assert "A" not in jtms.beliefs

    assert jtms.beliefs["C"].valid is None  # C ne peut plus être validé sans A

def test_graph_consistency_after_multiple_changes():
    jtms = JTMS()
    for name in "ABCDE":
        jtms.add_belief(name)

    jtms.add_justification(["A"], [], "B")
    jtms.add_justification(["B"], [], "C")
    jtms.add_justification(["C"], [], "D")
    jtms.add_justification(["D"], [], "E")

    jtms.set_belief_validity("A", True)

    assert jtms.beliefs["E"].valid is True

    jtms.set_belief_validity("A", False)
    for b in "BCDE":
        assert jtms.beliefs[b].valid is None

# -------------- ATMS ---------------
def test_simple_justification(atms):
    atms.add_assumption("A")
    atms.add_node("B")
    atms.add_justification(["A"], [], "B")

    assert atms.get_environments("B") == {frozenset({'A'})}

def test_multiple_justifications(atms):
    atms.add_assumption("A")
    atms.add_assumption("C")
    atms.add_node("B")
    atms.add_justification(["A"], [], "B")
    atms.add_justification(["C"], [], "B")

    envs = atms.get_environments("B")
    assert {"A"} in envs
    assert {"C"} in envs
    assert len(envs) == 2

def test_environment_removed_on_contradiction(atms):
    atms.add_assumption("A")
    atms.add_assumption("B")
    atms.add_node("C")

    atms.add_justification(["A", "B"], [], "C")
    atms.add_justification(["C"], [], "⊥")

    assert {"A", "B"} not in atms.get_environments("C")
    assert atms.get_environments("C") == set()

def test_environment_removed_on_contradiction_recurs(atms):
    atms.add_assumption("a")
    atms.add_assumption("b")
    atms.add_node("A")
    atms.add_node("B")
    atms.add_node("C")

    atms.add_justification(["a"], [], "A")
    atms.add_justification(["b"], [], "A")
    atms.add_justification(["b"], [], "B")
    atms.add_justification(["A", "B"], [], "C")

    assert atms.get_environments("C") == {frozenset({'a', 'b'}), frozenset({'b'})}
    
    atms.add_justification(["a"], [], "⊥")
    
    assert atms.get_environments("C") == {frozenset({'b'})}

def test_out_list_blocks_justification(atms):
    atms.add_assumption("A")
    atms.add_assumption("X")
    atms.add_node("C")
    atms.add_justification(["A"], ["X"], "C")

    envs = atms.get_environments("C")
    assert envs == {frozenset({"A"})}

def test_combined_environments(atms):
    atms.add_assumption("A")
    atms.add_assumption("B")
    atms.add_node("C")
    atms.add_justification(["A", "B"], [], "C")

    envs = atms.get_environments("C")
    assert envs == {frozenset({"A", "B"})}
    