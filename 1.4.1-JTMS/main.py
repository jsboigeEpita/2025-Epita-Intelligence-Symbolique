from belifs_loader import load_beliefs
from jtms import JTMS

if __name__ == "__main__":
    jtms = JTMS()
    jtms.add_belief("A")
    jtms.add_belief("B")
    jtms.add_justification(["B"], [], "A")
    jtms.add_justification([], ["A"], "B")

    jtms.set_belief_validity("A", True)

    # Une implémentation robuste ne plante pas, même si le cycle ne peut être validé logiquement
    assert jtms.beliefs["A"].non_monotonic is True
    assert jtms.beliefs["B"].non_monotonic is True

    jtms.visualize()
