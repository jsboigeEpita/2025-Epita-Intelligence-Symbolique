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


def test_blindness_wins_over_a_same_simple_name_candidate():
    """Inverted deliberately: the previous assertion encoded the defect.

    It read "a class found in the new surface is relocated, whatever else
    failed" -- so when the owning module never resolved on the new side, a class
    sharing its *simple name* somewhere else was reported RELOCATED. That is the
    tool asserting a move it could not have observed: no jar of that module was
    ever downloaded on the target side.

    It is also the exact shape of the wrong answer this tool exists to refuse.
    `Evidential*` lived in `arg.bipolar`; a same-simple-name hit in the unrelated
    `arg.eaf` is what made "promoted to arg.eaf" look true. Blindness must be
    tested first, and the candidate demoted to an annotated lead.
    """
    old = {"org.p.old.Widget": 59}
    owners = {"org.p.old.Widget": "arg.bipolar"}
    out = jld.classify_lost(
        old,
        {"org.p.new.Widget": 59},
        owners_old=owners,
        unresolved_new=["arg.bipolar"],
    )
    assert out["relocated"] == []
    fqcn, hint = out["indeterminate"][0]
    assert fqcn == "org.p.old.Widget"
    # The candidate is not thrown away -- it rides along, marked as unverified.
    assert "candidat non verifie" in hint and "org.p.new.Widget" in hint


def test_a_resolved_module_still_reports_a_relocation():
    """Anti-pendulum for the test above, and it is the half that matters.

    Making blindness win everywhere would be one edit away from a tool that never
    reports a relocation at all. When the owning module DID resolve on the target
    side, the observation is real and must stay a relocation.
    """
    out = jld.classify_lost(
        {"org.p.old.Widget": 59},
        {"org.p.new.Widget": 59},
        owners_old={"org.p.old.Widget": "arg.bipolar"},
        unresolved_new=[],
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


def _per_version(count, hist, unresolved=(), unreachable=()):
    return {
        "module_count": 1,
        "unresolved": list(unresolved),
        "unreachable": list(unreachable),
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
    rc = jld.main(["--from-version", "1.0", "--to-version", "2.0"])
    assert rc == 2
    assert "ne prouve pas une absence" in capsys.readouterr().err


class _Resp:
    """Minimal stand-in for the object urlopen returns."""

    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def test_get_classifies_a_404_as_absent_and_does_not_retry(monkeypatch):
    """A server that answered is a result, not an outage -- and not a retry."""
    calls = []

    def not_found(url, timeout=0):
        calls.append(url)
        raise jld.urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(jld.urllib.request, "urlopen", not_found)
    monkeypatch.setattr(jld.time, "sleep", lambda _s: None)
    assert jld._get("http://repo/x", timeout=1) == (None, jld.FETCH_ABSENT)
    assert len(calls) == 1, "retrying a permanent answer blurs the distinction"


def test_get_retries_a_transient_failure_then_reports_unreachable(monkeypatch):
    """`Connection reset` is the failure that used to be read as a clean absence."""
    calls = []

    def reset(url, timeout=0):
        calls.append(url)
        raise OSError("Connection reset by peer")

    monkeypatch.setattr(jld.urllib.request, "urlopen", reset)
    monkeypatch.setattr(jld.time, "sleep", lambda _s: None)
    assert jld._get("http://repo/x", timeout=1, attempts=3) == (
        None,
        jld.FETCH_UNREACHABLE,
    )
    assert len(calls) == 3


def test_get_recovers_when_a_retry_succeeds(monkeypatch):
    """Non-vacuity for the retry: it must be able to end in a success.

    Without this, `attempts` could be wired to a no-op and both tests above would
    still pass -- three failed calls and one failed call are indistinguishable
    when the only assertion is on the final status.
    """
    calls = []

    def flaky(url, timeout=0):
        calls.append(url)
        if len(calls) < 2:
            raise OSError("Connection reset by peer")
        return _Resp(b"PKcontent")

    monkeypatch.setattr(jld.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(jld.time, "sleep", lambda _s: None)
    assert jld._get("http://repo/x", timeout=1) == (b"PKcontent", jld.FETCH_OK)
    assert len(calls) == 2


def test_fetch_jar_rejects_a_404_html_body(monkeypatch):
    """An HTML body means the front answered: absence, not outage."""
    monkeypatch.setattr(
        jld, "_get", lambda url, timeout=0: (b"<html>404</html>", jld.FETCH_OK)
    )
    assert jld.fetch_jar("http://repo", "org.p", "a", "1.0") == (
        None,
        jld.FETCH_ABSENT,
    )
    blob = _jar({"org/p/A.class": 59})
    monkeypatch.setattr(jld, "_get", lambda url, timeout=0: (blob, jld.FETCH_OK))
    body, status = jld.fetch_jar("http://repo", "org.p", "a", "1.0")
    assert body is not None and status == jld.FETCH_OK


def test_fetch_jar_propagates_unreachable(monkeypatch):
    monkeypatch.setattr(
        jld, "_get", lambda url, timeout=0: (None, jld.FETCH_UNREACHABLE)
    )
    assert jld.fetch_jar("http://repo", "org.p", "a", "1.0") == (
        None,
        jld.FETCH_UNREACHABLE,
    )


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
        return _jar({"org/p/A.class": 59}), jld.FETCH_OK

    monkeypatch.setattr(jld, "fetch_jar", fake_fetch)
    index, owners, resolved, unresolved, unreachable = jld.collect_version(
        jld.MAVEN_CENTRAL, "org.tweetyproject", [module], "1.31"
    )
    assert seen == {"group": expect_group, "artifact": expect_artifact}
    assert resolved == [module] and unresolved == [] and unreachable == []
    assert index == {"org.p.A": 59}
    assert owners == {"org.p.A": module}


@pytest.mark.parametrize(
    "status, expect_unreachable",
    [
        # An absence is an answer about the repository: unresolved, but observed.
        ("absent", []),
        # An outage is an answer about us: unresolved AND never looked at.
        ("unreachable", ["arg.bipolar"]),
    ],
)
def test_collect_version_separates_absence_from_unreachability(
    monkeypatch, status, expect_unreachable
):
    monkeypatch.setattr(
        jld, "fetch_jar", lambda repo, g, a, v, timeout=0: (None, status)
    )
    index, owners, resolved, unresolved, unreachable = jld.collect_version(
        jld.MAVEN_CENTRAL, "org.tweetyproject", ["arg.bipolar"], "1.28"
    )
    assert (index, owners, resolved) == ({}, {}, [])
    assert unresolved == ["arg.bipolar"]
    assert unreachable == expect_unreachable


def test_collect_version_records_unresolved_modules_without_owners():
    def fake_fetch(repo, group, artifact, version, timeout=0):
        return None, jld.FETCH_ABSENT

    import scripts.maintenance.java_lib_version_diff as mod

    original, mod.fetch_jar = mod.fetch_jar, fake_fetch
    try:
        index, owners, resolved, unresolved, unreachable = jld.collect_version(
            jld.MAVEN_CENTRAL, "org.tweetyproject", ["arg.bipolar"], "1.28"
        )
    finally:
        mod.fetch_jar = original
    assert (index, owners, resolved) == ({}, {}, [])
    assert unresolved == ["arg.bipolar"] and unreachable == []


# ------------------------------------------------- control: BOTH sides, not one


def _diff(source, target, old_index=None, new_index=None):
    """`source`/`target` are (unresolved, unreachable) pairs for each side."""
    return jld.diff_versions(
        old_index if old_index is not None else {"org.p.A": 59},
        new_index if new_index is not None else {"org.p.A": 59},
        group="org.p",
        from_version="1.0",
        to_version="2.0",
        per_version={
            "1.0": _per_version(1, [(59, 1)], *source),
            "2.0": _per_version(1, [(59, 1)], *target),
        },
    )


def test_an_unreachable_source_module_voids_the_control():
    """The measured symptom, and the reason the source side must be read.

    One failed GET on a source module turned `perdues=75` into `perdues=0`: the
    classes that module owns never entered `old_index`, so they could not be
    reported lost. The report then printed "un zero est semantique" and `main`
    returned 0. Every number in that run was instrumental, and nothing said so.
    """
    res = _diff((["arg.bipolar"], ["arg.bipolar"]), ([], []))
    assert res["control"]["ok"] is False
    assert res["control"]["unreachable_source"] == ["arg.bipolar"]
    text = jld.render_report(res)
    assert "INJOIGNABLE" in text
    assert "un zero est semantique" not in text


def test_an_unreachable_target_module_voids_the_control():
    res = _diff(([], []), (["arg.bipolar"], ["arg.bipolar"]))
    assert res["control"]["ok"] is False
    assert res["control"]["unreachable_target"] == ["arg.bipolar"]
    assert "INJOIGNABLE" in jld.render_report(res)


def test_a_merely_absent_source_module_does_not_void_the_control():
    """Anti-pendulum: a guard that reddens on a healthy run gets switched off.

    Comparing two versions with one module list normally leaves modules missing
    from the older side -- they contribute no class to `old_index`, so they cannot
    manufacture a false zero. That absence is reported, not treated as a failure;
    only unreachability is.
    """
    res = _diff((["arg.eaf"], []), ([], []))
    assert res["control"]["ok"] is True
    text = jld.render_report(res)
    assert "note: 1 module(s) absent(s) de la version source" in text
    assert "un zero est semantique" in text


def test_control_stays_false_when_the_source_index_is_empty():
    """The pre-existing guard must survive the widening."""
    res = _diff(([], []), ([], []), old_index={})
    assert res["control"]["ok"] is False
    assert "index de depart vide" in jld.render_report(res)


def test_main_exits_1_when_a_source_module_is_unreachable(monkeypatch, capsys):
    def fake_fetch(repo, group, artifact, version, timeout=0):
        if artifact == "bipolar" and version == "1.0":
            return None, jld.FETCH_UNREACHABLE
        return _jar({"org/p/A.class": 59}), jld.FETCH_OK

    monkeypatch.setattr(jld, "fetch_jar", fake_fetch)
    rc = jld.main(
        [
            "--from-version",
            "1.0",
            "--to-version",
            "2.0",
            "--modules",
            "arg.bipolar",
            "logics.pl",
        ]
    )
    assert rc == 1
    assert "INJOIGNABLE" in capsys.readouterr().out


def test_main_exits_0_on_a_fully_resolved_comparison(monkeypatch, capsys):
    """Non-vacuity for the rc test above: `main` must be able to return 0.

    Without this pair, wiring `main` to `return 1` unconditionally would keep the
    failure test green -- an exit code asserted only on the failing side measures
    nothing.
    """
    monkeypatch.setattr(
        jld,
        "fetch_jar",
        lambda *a, **k: (_jar({"org/p/A.class": 59}), jld.FETCH_OK),
    )
    rc = jld.main(
        [
            "--from-version",
            "1.0",
            "--to-version",
            "2.0",
            "--modules",
            "arg.bipolar",
            "logics.pl",
        ]
    )
    assert rc == 0
    assert "un zero est semantique" in capsys.readouterr().out


# ------------------------------------------------- aggregator axis (wired, #1882)


_POM = """<project>
  <dependencies>
    <dependency><groupId>org.tweetyproject</groupId>
      <artifactId>commons</artifactId><version>1.28</version></dependency>
    <dependency><groupId>org.tweetyproject.arg</groupId>
      <artifactId>bipolar</artifactId><version>1.28</version></dependency>
    <dependency><groupId>com.thirdparty</groupId>
      <artifactId>solver</artifactId><version>3.0</version></dependency>
  </dependencies>
</project>"""


def test_aggregator_modules_maps_group_segments_and_drops_third_party(monkeypatch):
    monkeypatch.setattr(
        jld, "_get", lambda url, timeout=0: (_POM.encode("utf-8"), jld.FETCH_OK)
    )
    modules, status = jld.aggregator_modules(
        "http://repo", "org.tweetyproject", "tweety-full", "1.28"
    )
    assert status == jld.FETCH_OK
    # `com.thirdparty:solver` is closure, not a module of the library. Counting it
    # would inflate every gap figure computed from this list.
    assert modules == ["arg.bipolar", "commons"]


def test_aggregator_modules_reports_an_unreachable_pom_as_such(monkeypatch):
    """An unreachable POM must not read as an aggregator that declares nothing."""
    monkeypatch.setattr(
        jld, "_get", lambda url, timeout=0: (None, jld.FETCH_UNREACHABLE)
    )
    assert jld.aggregator_modules("http://repo", "org.p", "full", "1.0") == (
        [],
        jld.FETCH_UNREACHABLE,
    )


def test_publication_gaps_is_computed_over_the_declared_set(monkeypatch, capsys):
    """The #1874 trap, end to end: the umbrella resolves, its parts do not.

    The regression this guards is subtle: computing gaps against the *compared*
    module set (`--modules`) would report every module the caller did not ask
    about as a publication gap -- a figure that grows as the caller narrows the
    question, which is the opposite of a measurement.
    """
    monkeypatch.setattr(
        jld, "_get", lambda url, timeout=0: (_POM.encode("utf-8"), jld.FETCH_OK)
    )
    # `commons` is published at 1.28; `arg.bipolar` is declared but published only
    # elsewhere -- the hole in the middle of a published sequence.
    monkeypatch.setattr(
        jld,
        "published_versions",
        lambda repo, group, artifact, timeout=0: (
            ["1.27", "1.28"] if artifact == "commons" else ["1.27", "1.29"]
        ),
    )
    monkeypatch.setattr(
        jld,
        "fetch_jar",
        lambda repo, g, a, v, timeout=0: (_jar({"org/p/A.class": 59}), jld.FETCH_OK),
    )
    rc = jld.main(
        [
            "--from-version",
            "1.28",
            "--to-version",
            "1.29",
            "--aggregator",
            "tweety-full",
            "--modules",
            "commons",
        ]
    )
    out = capsys.readouterr().out
    # Only `arg.bipolar` is a gap. `commons` resolves; nothing else is invented.
    assert "trous=1" in out
    assert "TROU  arg.bipolar (publie ailleurs en 1.27, 1.29)" in out
    assert rc == 0


def test_a_gap_never_published_anywhere_is_named_differently(monkeypatch, capsys):
    """Missing-at-this-version and never-published-at-all differ in action."""
    monkeypatch.setattr(
        jld, "_get", lambda url, timeout=0: (_POM.encode("utf-8"), jld.FETCH_OK)
    )
    monkeypatch.setattr(
        jld, "published_versions", lambda repo, group, artifact, timeout=0: []
    )
    monkeypatch.setattr(
        jld,
        "fetch_jar",
        lambda repo, g, a, v, timeout=0: (_jar({"org/p/A.class": 59}), jld.FETCH_OK),
    )
    jld.main(
        [
            "--from-version",
            "1.28",
            "--to-version",
            "1.29",
            "--aggregator",
            "tweety-full",
            "--modules",
            "commons",
        ]
    )
    assert "aucune version publiee" in capsys.readouterr().out


def _with_aggregator(**over):
    agg = {
        "artifact": "full",
        "status": jld.FETCH_OK,
        "declared": ["commons"],
        "gaps": [],
        "gap_versions": {},
        "metadata_only": [],
        "not_aggregated": [],
    }
    agg.update(over)
    return jld.diff_versions(
        {"org.p.A": 59},
        {"org.p.A": 59},
        group="org.p",
        from_version="1.0",
        to_version="2.0",
        per_version={
            "1.0": dict(_per_version(1, [(59, 1)]), aggregator=agg),
            "2.0": _per_version(1, [(59, 1)]),
        },
    )


def test_metadata_only_names_the_gap_between_two_instruments():
    """Metadata claims the version, the jar does not answer: keep the delta.

    Arbitrating which one is right throws away the only figure that measures what
    a metadata-only reading cannot see.
    """
    res = _with_aggregator(metadata_only=["commons"])
    assert "METADATA-SEULE commons" in jld.render_report(res)


def test_gap_listing_says_how_many_it_did_not_print():
    """A cut that leaves no trace reads as if that had been all of them."""
    res = _with_aggregator(
        declared=[f"m{i}" for i in range(36)],
        gaps=[f"m{i}" for i in range(36)],
    )
    assert "24 autre(s) trou(s) non listes" in jld.render_report(res)


def test_relocation_candidates_from_two_unrelated_modules_are_all_listed():
    """The falsifiable control, in the shape the real sweep produced.

    Measured on Central, `arg.*` 1.29 -> 1.31: 84 classes lost, **12** of which
    have their simple name present on the target side -- so the relocation branch
    is genuinely reachable on real data. The narrow two-module run quoted in the
    PR body had a simple-name overlap of exactly **0**, so its `relocalisees=0`
    was guaranteed whatever the code did: it could not have failed.

    The 12 real hits are the trap itself: `CompleteReasoner` exists in `arg.aba`,
    `arg.adf` AND `arg.bipolar` -- three unrelated formalisms reusing one generic
    name. The contract is that every candidate is surfaced with its full package,
    so the reader rejects the move rather than the tool asserting it.
    """
    out = jld.classify_lost(
        {"org.p.bipolar.evidential.CompleteReasoner": 59},
        {
            "org.p.aba.CompleteReasoner": 59,
            "org.p.adf.CompleteReasoner": 59,
        },
        owners_old={"org.p.bipolar.evidential.CompleteReasoner": "arg.bipolar"},
        unresolved_new=[],
    )
    assert out["deleted"] == [] and out["indeterminate"] == []
    fqcn, where = out["relocated"][0]
    assert fqcn == "org.p.bipolar.evidential.CompleteReasoner"
    # Both candidates, full package, so the reader can reject both.
    assert where == "org.p.aba.CompleteReasoner, org.p.adf.CompleteReasoner"


# ------------------------------------------------- CLI surface reachable from CLI


def test_main_refuses_an_explicitly_empty_modules_flag(capsys):
    """`--modules` with no value used to run a full network discovery instead.

    Silently different, on a much larger population, under a flag that says the
    opposite. The caller who typed `--modules` meant to restrict the run.
    """
    rc = jld.main(["--from-version", "1.0", "--to-version", "2.0", "--modules"])
    assert rc == 2
    assert "sans valeur" in capsys.readouterr().err


def test_include_inner_reaches_index_jar_from_the_cli(monkeypatch, capsys):
    """`skip_inner` was documented in the PR body and unreachable from the CLI.

    Both counts are correct -- they do not measure the same object -- but only one
    of them could be produced, so the documented comparison could not be made.
    """
    blob = _jar({"org/p/A.class": 59, "org/p/A$Inner.class": 59})
    monkeypatch.setattr(jld, "fetch_jar", lambda *a, **k: (blob, jld.FETCH_OK))
    base = ["--from-version", "1.0", "--to-version", "2.0", "--modules", "commons"]

    jld.main(base)
    assert "classes=1" in capsys.readouterr().out

    jld.main(base + ["--include-inner"])
    assert "classes=2" in capsys.readouterr().out


def test_limit_zero_shows_every_class_instead_of_none(monkeypatch, capsys):
    """`--limit 0` silently produced an empty detail list.

    An empty list of deletions under a header saying `supprimees=3` reads as a
    rendering quirk at best and as "there were none" at worst.
    """
    old = {f"org.p.Gone{i}": 59 for i in range(3)}

    def fetch(repo, group, artifact, version, timeout=0, **kw):
        blob = (
            _jar({f"org/p/Gone{i}.class": 59 for i in range(3)})
            if version == "1.0"
            else _jar({"org/p/Kept.class": 59})
        )
        return blob, jld.FETCH_OK

    monkeypatch.setattr(jld, "fetch_jar", fetch)
    jld.main(
        [
            "--from-version",
            "1.0",
            "--to-version",
            "2.0",
            "--modules",
            "commons",
            "--limit",
            "0",
        ]
    )
    out = capsys.readouterr().out
    assert "supprimees=3" in out
    assert all(f"SUPPRIMEE    org.p.Gone{i}" in out for i in range(3))
    assert old  # the population is non-empty, so the assertion above can fail


def test_a_relocation_candidate_names_its_host_module():
    """The host module is what makes a collision rejectable at a glance.

    `owners_by_version[to_version]` was built on every run and then discarded, so
    the report showed `CompleteReasoner -> org.p.adf.CompleteReasoner` without the
    one fact that settles it: the candidate lives in an unrelated formalism.
    """
    out = jld.classify_lost(
        {"org.p.bipolar.CompleteReasoner": 59},
        {"org.p.adf.CompleteReasoner": 59},
        owners_old={"org.p.bipolar.CompleteReasoner": "arg.bipolar"},
        owners_new={"org.p.adf.CompleteReasoner": "arg.adf"},
    )
    assert out["relocated"] == [
        ("org.p.bipolar.CompleteReasoner", "org.p.adf.CompleteReasoner (arg.adf)")
    ]


def test_the_report_refuses_rather_than_contradicting_itself():
    """Without `owners_old`, INDETERMINATE cannot be reached at all.

    Every lost class would be printed SUPPRIMEE by the same report that states the
    target side did not fully resolve. A report that contradicts itself is worse
    than one that refuses to conclude, so the control now declines.
    """
    res = jld.diff_versions(
        {"org.p.A": 59},
        {},
        group="org.p",
        from_version="1.0",
        to_version="2.0",
        per_version={
            "1.0": _per_version(1, [(59, 1)]),
            "2.0": _per_version(0, [], unresolved=["arg.bipolar"]),
        },
    )
    assert res["control"]["ok"] is False
    assert res["control"]["attribution_missing"] is True
    assert "attribution des classes indisponible" in jld.render_report(res)


def test_attribution_is_available_when_owners_are_passed():
    """Anti-pendulum: the guard above must not fire on a well-formed call."""
    res = jld.diff_versions(
        {"org.p.A": 59},
        {},
        group="org.p",
        from_version="1.0",
        to_version="2.0",
        per_version={
            "1.0": _per_version(1, [(59, 1)]),
            "2.0": _per_version(0, [], unresolved=["arg.bipolar"]),
        },
        owners_old={"org.p.A": "arg.bipolar"},
    )
    assert res["control"]["attribution_missing"] is False
    text = jld.render_report(res)
    assert "attribution des classes indisponible" not in text
    assert "INDETERMINEES, pas supprimees" in text


def test_skip_inner_tests_the_simple_name_not_the_whole_path():
    """A dollar sign in a package directory is legal and must not hide a class.

    Testing the full path drops every class under such a directory -- a silent
    exclusion, invisible in the count it shrinks.
    """
    blob = _jar(
        {
            "org/p/A.class": 59,
            "org/p/A$Inner.class": 59,
            "org/p$odd/B.class": 59,
        }
    )
    kept = jld.index_jar(blob)
    assert "org.p.A" in kept
    assert "org.p.A$Inner" not in kept
    # The one the path-wide test used to swallow.
    assert "org.p$odd.B" in kept
    assert len(jld.index_jar(blob, skip_inner=False)) == 3
