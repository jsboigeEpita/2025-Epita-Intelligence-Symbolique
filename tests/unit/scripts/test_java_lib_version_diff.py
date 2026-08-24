"""Offline tests for scripts/maintenance/java_lib_version_diff.py (#1874).

Every fixture is an in-memory zip built here, so the suite never touches the
network and never needs a Maven repository. What is verified is precisely the
three failure modes the tool exists to catch:

* an aggregator that resolves while its modules are absent,
* a lost class wrongly reported as relocated (or wrongly as deleted),
* a bytecode level that no downstream bridge can consume.

The bytecode fixtures are synthesised, not real class files: the tool reads
exactly bytes 0-7 (magic + major), so an 8-byte header plus filler exercises the
same code path a 40 kB class would.
"""

import io
import zipfile

import pytest

from scripts.maintenance import java_lib_version_diff as jld


def _class_bytes(major: int) -> bytes:
    """Minimal class-file head: CAFEBABE, minor=0, major, then filler."""
    return (
        jld.CLASS_MAGIC + b"\x00\x00" + bytes([major >> 8, major & 0xFF]) + b"\x00" * 16
    )


def _jar(entries: dict) -> bytes:
    """entries: {'a/b/C.class': major_int} plus any non-class name -> bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, value in entries.items():
            zf.writestr(name, _class_bytes(value) if isinstance(value, int) else value)
    return buf.getvalue()


# ------------------------------------------------------------------ index_jar


def test_index_jar_maps_fqcn_to_major():
    blob = _jar({"org/x/A.class": 52, "org/x/y/B.class": 59})
    assert jld.index_jar(blob) == {"org.x.A": 52, "org.x.y.B": 59}


def test_index_jar_skips_inner_classes_by_default():
    blob = _jar({"org/x/A.class": 59, "org/x/A$Inner.class": 59})
    assert set(jld.index_jar(blob)) == {"org.x.A"}
    assert set(jld.index_jar(blob, skip_inner=False)) == {"org.x.A", "org.x.A$Inner"}


def test_index_jar_ignores_non_class_and_non_magic_entries():
    blob = _jar(
        {
            "org/x/A.class": 59,
            "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n",
            "org/x/Broken.class": b"not a class file at all",
        }
    )
    assert set(jld.index_jar(blob)) == {"org.x.A"}


# ------------------------------------------------------- bytecode / max_major


def test_bytecode_histogram_orders_by_frequency():
    index = {"a": 59, "b": 59, "c": 54}
    assert jld.bytecode_histogram(index) == [(59, 2), (54, 1)]


def test_max_major_flags_a_library_no_java8_bridge_can_consume():
    # The IKVM-8 question: downgrading does not help when every class is > 52.
    index = {"a": 59, "b": 54}
    assert jld.max_major(index) == 59
    assert jld.max_major({}) is None


# ---------------------------------------------------------------- classify_lost


def test_deleted_class_is_reported_as_deleted_not_relocated():
    old = {"org.p.arg.bipolar.syntax.EvidentialArgumentationFramework": 59}
    new = {"org.p.arg.bipolar.syntax.BipolarArgumentationFramework": 59}
    out = jld.classify_lost(old, new)
    assert out["relocated"] == []
    assert [f for f, _ in out["deleted"]] == [
        "org.p.arg.bipolar.syntax.EvidentialArgumentationFramework"
    ]


def test_relocated_class_names_its_new_home():
    old = {"org.p.old.Widget": 59}
    new = {"org.p.brandnew.Widget": 59}
    out = jld.classify_lost(old, new)
    assert out["deleted"] == []
    assert out["relocated"] == [("org.p.old.Widget", "org.p.brandnew.Widget")]


def test_relocation_search_covers_modules_the_aggregator_omits():
    """The blind spot: a class moved into a module the umbrella does not pull.

    Searching only the aggregator's closure would report DELETED. Feeding the
    union (aggregated + non-aggregated) is what makes the verdict trustworthy.
    """
    old = {"org.p.old.Widget": 59}
    aggregated_new = {"org.p.core.Other": 59}
    outside_new = {"org.p.extra.Widget": 59}

    blind = jld.classify_lost(old, aggregated_new)
    assert [f for f, _ in blind["deleted"]] == ["org.p.old.Widget"]

    full = jld.classify_lost(old, {**aggregated_new, **outside_new})
    assert full["deleted"] == []
    assert full["relocated"] == [("org.p.old.Widget", "org.p.extra.Widget")]


def test_unchanged_index_loses_nothing():
    same = {"org.p.A": 59, "org.p.B": 59}
    out = jld.classify_lost(same, dict(same))
    assert out == {"relocated": [], "deleted": [], "indeterminate": []}


def test_an_unresolved_target_module_yields_indeterminate_not_deleted():
    """The defect the first live run exposed on version 1.28.

    413 classes were printed as SUPPRIMEE while the target side had resolved zero
    modules. Nothing was deleted -- nothing was looked at. A verdict read off an
    instrument that produced no positive for that module is an artefact.
    """
    old = {"org.p.arg.bipolar.Gone": 59, "org.p.logics.pl.Kept": 59}
    owners = {
        "org.p.arg.bipolar.Gone": "arg.bipolar",
        "org.p.logics.pl.Kept": "logics.pl",
    }
    new = {}
    out = jld.classify_lost(old, new, owners_old=owners, unresolved_new=["arg.bipolar"])
    assert [f for f, _ in out["indeterminate"]] == ["org.p.arg.bipolar.Gone"]
    # logics.pl DID resolve (it is not in unresolved_new) and came back empty,
    # so its loss is a real deletion and must stay one.
    assert [f for f, _ in out["deleted"]] == ["org.p.logics.pl.Kept"]


def test_relocation_wins_over_indeterminate():
    """A class found in the new surface is relocated, whatever else failed."""
    old = {"org.p.old.Widget": 59}
    owners = {"org.p.old.Widget": "arg.bipolar"}
    out = jld.classify_lost(
        old,
        {"org.p.new.Widget": 59},
        owners_old=owners,
        unresolved_new=["arg.bipolar"],
    )
    assert out["indeterminate"] == []
    assert out["relocated"] == [("org.p.old.Widget", "org.p.new.Widget")]


def test_a_same_simple_name_elsewhere_is_only_a_candidate():
    """classify_lost is deliberately generous; the caller must still look.

    This is the arg.eaf trap: `EAF` meant Epistemic, not Evidential. The tool
    surfaces the candidate with its full package so the reader can reject it --
    it never asserts the move happened.
    """
    old = {"org.p.evidential.Framework": 59}
    new = {"org.p.epistemic.Framework": 59}
    out = jld.classify_lost(old, new)
    fqcn, where = out["relocated"][0]
    assert fqcn == "org.p.evidential.Framework"
    assert where == "org.p.epistemic.Framework"  # different package -> reader decides


# ------------------------------------------------- publication gaps / coverage


def test_publication_gap_detects_aggregator_declaring_absent_modules():
    """#1874: tweety-full:1.28 resolves, its 47 modules do not exist at 1.28."""
    declared = ["arg.dung", "arg.bipolar", "logics.pl"]
    assert jld.publication_gaps(declared, resolvable=[]) == declared
    assert jld.publication_gaps(declared, resolvable=declared) == []
    assert jld.publication_gaps(declared, resolvable=["logics.pl"]) == [
        "arg.dung",
        "arg.bipolar",
    ]


def test_not_aggregated_lists_published_modules_outside_the_umbrella():
    published = ["arg.dung", "arg.bipolar", "arg.extended"]
    aggregated = ["arg.dung", "arg.bipolar"]
    assert jld.not_aggregated(published, aggregated) == ["arg.extended"]


# --------------------------------------------------------- diff_versions/control


def _per_version(count, hist, unresolved=()):
    return {
        "module_count": 1,
        "unresolved": list(unresolved),
        "class_count": count,
        "bytecode": hist,
    }


def test_control_fails_when_the_reference_side_is_empty():
    """A zero from an instrument that never produced a positive proves nothing."""
    res = jld.diff_versions(
        {},
        {"org.p.A": 59},
        group="org.p",
        from_version="1.0",
        to_version="2.0",
        per_version={
            "1.0": _per_version(0, []),
            "2.0": _per_version(1, [(59, 1)]),
        },
    )
    assert res["control"]["ok"] is False
    assert "index de depart vide" in jld.render_report(res)


def test_control_fails_when_the_target_side_did_not_fully_resolve():
    """An unpublished target must not be readable as an API deletion."""
    old = {"org.p.A": 59}
    res = jld.diff_versions(
        old,
        {},
        group="org.p",
        from_version="1.27",
        to_version="1.28",
        per_version={
            "1.27": _per_version(1, [(59, 1)]),
            "1.28": _per_version(0, [], unresolved=["arg.bipolar"]),
        },
        owners_old={"org.p.A": "arg.bipolar"},
    )
    assert res["control"]["ok"] is False
    assert res["lost"]["deleted"] == []
    assert [f for f, _ in res["lost"]["indeterminate"]] == ["org.p.A"]
    text = jld.render_report(res)
    assert "INDETERMINEES, pas supprimees" in text
    assert "SUPPRIMEE" not in text


def test_control_passes_and_report_names_both_verdicts():
    old = {"org.p.Gone": 59, "org.p.old.Moved": 59, "org.p.Kept": 59}
    new = {"org.p.new.Moved": 59, "org.p.Kept": 59, "org.p.Fresh": 59}
    res = jld.diff_versions(
        old,
        new,
        group="org.p",
        from_version="1.0",
        to_version="2.0",
        per_version={
            "1.0": _per_version(3, [(59, 3)]),
            "2.0": _per_version(3, [(59, 3)]),
        },
    )
    assert res["control"]["ok"] is True
    assert res["gained"] == ["org.p.Fresh", "org.p.new.Moved"]
    text = jld.render_report(res)
    assert "SUPPRIMEE    org.p.Gone" in text
    assert "RELOCALISEE? org.p.old.Moved -> org.p.new.Moved" in text
    assert "relocalisees=1, supprimees=1, indeterminees=0" in text


def test_report_surfaces_unresolved_modules():
    res = jld.diff_versions(
        {"org.p.A": 59},
        {"org.p.A": 59},
        group="org.p",
        from_version="1.0",
        to_version="2.0",
        per_version={
            "1.0": _per_version(1, [(59, 1)]),
            "2.0": _per_version(1, [(59, 1)], unresolved=["arg.bipolar"]),
        },
    )
    text = jld.render_report(res)
    assert "NON publies (1): arg.bipolar" in text


def test_main_refuses_to_run_without_modules_and_without_discovery(monkeypatch, capsys):
    monkeypatch.setattr(jld, "list_repo_children", lambda *a, **k: [])
    rc = jld.main(["--from-version", "1.0", "--to-version", "2.0", "--modules"])
    assert rc == 2
    assert "ne prouve pas une absence" in capsys.readouterr().err


def test_fetch_jar_rejects_a_404_html_body(monkeypatch):
    monkeypatch.setattr(jld, "_get", lambda url, timeout=0: b"<html>404</html>")
    assert jld.fetch_jar("http://repo", "org.p", "a", "1.0") is None
    monkeypatch.setattr(jld, "_get", lambda url, timeout=0: _jar({"org/p/A.class": 59}))
    assert jld.fetch_jar("http://repo", "org.p", "a", "1.0") is not None


@pytest.mark.parametrize(
    "module, expect_group, expect_artifact",
    [
        ("arg.bipolar", "org.tweetyproject.arg", "bipolar"),
        ("cli", "org.tweetyproject", "cli"),
    ],
)
def test_collect_version_splits_nested_group_segments(
    monkeypatch, module, expect_group, expect_artifact
):
    seen = {}

    def fake_fetch(repo, group, artifact, version, timeout=0):
        seen["group"], seen["artifact"] = group, artifact
        return _jar({"org/p/A.class": 59})

    monkeypatch.setattr(jld, "fetch_jar", fake_fetch)
    index, owners, resolved, unresolved = jld.collect_version(
        jld.MAVEN_CENTRAL, "org.tweetyproject", [module], "1.31"
    )
    assert seen == {"group": expect_group, "artifact": expect_artifact}
    assert resolved == [module] and unresolved == []
    assert index == {"org.p.A": 59}
    assert owners == {"org.p.A": module}


def test_collect_version_records_unresolved_modules_without_owners():
    monkey_index = {}

    def fake_fetch(repo, group, artifact, version, timeout=0):
        return None

    import scripts.maintenance.java_lib_version_diff as mod

    original, mod.fetch_jar = mod.fetch_jar, fake_fetch
    try:
        index, owners, resolved, unresolved = jld.collect_version(
            jld.MAVEN_CENTRAL, "org.tweetyproject", ["arg.bipolar"], "1.28"
        )
    finally:
        mod.fetch_jar = original
    assert (index, owners, resolved) == (monkey_index, {}, [])
    assert unresolved == ["arg.bipolar"]
