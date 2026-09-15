"""#2252: the 4-arg preset encodes mutual destruction, not the Nixon diamond.

Renamed by arbitration R1007 (D1). The old name ``nixon_diamond`` claimed a
semantics the edges never had: the docstring listed attacks the code does not
build, the classic diamond has TWO stable extensions, and this framework has
exactly ONE. Zero consumers demanded the diamond semantics, and the canonical
two-extension diamond already lives under the same name in ``abs_arg_dung`` —
the homonymy is what hid the difference for so long.

Born-red pair: before the rename, ``mutual_destruction`` does not exist
(AttributeError) and ``nixon_diamond`` still does (hasattr True). Both flip
with the rename; the third test pins where the canonical diamond actually
lives so the cross-reference stays honest.
"""

from argumentation_analysis.agents.core.logic.dung_native import DungFramework


def test_mutual_destruction_builds_the_measured_edges():
    fw = DungFramework.mutual_destruction()
    assert sorted(fw.arguments) == ["hawk", "pacifist", "quaker", "republican"]
    assert fw.attacks == {
        ("quaker", "hawk"),
        ("republican", "pacifist"),
        ("hawk", "pacifist"),
        ("pacifist", "hawk"),
    }
    # Measured semantics (#2252): quaker/republican unattacked, ONE stable
    # extension, hawk/pacifist rejected under every semantics.
    assert fw.grounded_extension() == frozenset({"quaker", "republican"})
    stable = fw.stable_extensions()
    assert len(stable) == 1
    status = fw.get_argument_status("hawk")
    assert all(
        status[k] is False
        for k in ("in_grounded", "credulously_accepted", "skeptically_accepted")
    )


def test_nixon_diamond_is_not_redeclared_on_dung_framework():
    # The name belongs to the canonical diamond in abs_arg_dung; redeclaring
    # it here would resurrect the homonymy the rename removed.
    assert not hasattr(DungFramework, "nixon_diamond")


def test_the_canonical_diamond_lives_in_abs_arg_dung():
    from abs_arg_dung.backends.generators import generate_classic_examples

    nixon = generate_classic_examples()["nixon_diamond"]
    args, attacks = nixon[0], nixon[1]
    stable = DungFramework.from_args_and_attacks(args, attacks).stable_extensions()
    assert len(stable) == 2, (
        "the canonical Nixon diamond must keep TWO stable extensions — if this "
        "fails, the cross-reference in mutual_destruction's docstring is stale"
    )
