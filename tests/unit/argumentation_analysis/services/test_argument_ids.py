"""Tests for the shared ``arg_N`` fallacy-target resolver (#2744 review).

The resolver lives once in ``argumentation_analysis.services.argument_ids``
and is bound — not copied — by both consumers: ``invoke_callables``
(orchestration) and ``semantic_index_service`` (service layer). These tests
pin the shared semantics and redden if either side re-states the convention.
"""

from argumentation_analysis.services.argument_ids import (
    ARG_ID_RE,
    FALLACY_TARGET_KEYS,
    read_fallacy_target,
    resolve_target_argument_index,
)
from argumentation_analysis.services.semantic_index_service import (
    SemanticIndexService,
)


class TestResolveTargetArgumentIndex:
    """Semantics of the single resolver (#1629/#1633)."""

    def test_ids_are_one_based(self):
        """``arg_1`` is the first argument, ``arg_N`` the Nth."""
        assert resolve_target_argument_index("arg_1", 3) == 0
        assert resolve_target_argument_index("arg_3", 3) == 2

    def test_out_of_range_resolves_to_nothing(self):
        """The caller must not guess (#1019): beyond the argument count or
        below the 1-based floor, there is no association."""
        assert resolve_target_argument_index("arg_4", 3) is None
        assert resolve_target_argument_index("arg_0", 3) is None

    def test_malformed_resolves_to_nothing(self):
        """``paragraph_N`` ids and padded garbage are not ``arg_N`` ids."""
        assert resolve_target_argument_index("paragraph_2", 3) is None
        assert resolve_target_argument_index("arg_1 extra", 3) is None

    def test_absent_target_resolves_to_nothing(self):
        assert resolve_target_argument_index(None, 3) is None
        assert resolve_target_argument_index("", 3) is None

    def test_bare_integer_resolves_to_nothing(self):
        """#2744 review: no producer writes an int into the three target keys
        (the only int writer, ``complex_fallacy_analyzer``, fills
        ``logical_flows`` — not fallacy records). The shared resolver sends
        every target through the ``arg_N`` regex, so an int is malformed, not
        a 0-based index — the drift the old service-side copy carried."""
        assert resolve_target_argument_index(1, 3) is None
        assert resolve_target_argument_index(0, 3) is None


class TestReadFallacyTarget:
    """First non-empty target reference across the #1633 key tuple."""

    def test_every_key_convention_is_read(self):
        assert read_fallacy_target({"target_argument": "arg_1"}) == "arg_1"
        assert read_fallacy_target({"target_argument_id": "arg_2"}) == "arg_2"
        assert read_fallacy_target({"target_arg_id": "arg_3"}) == "arg_3"

    def test_none_value_falls_through_to_next_key(self):
        """Producers emit the key with a ``None`` value when a detection has
        no target (#1633): the loop must not stop on it."""
        record = {"target_argument": None, "target_argument_id": "arg_1"}
        assert read_fallacy_target(record) == "arg_1"

    def test_no_target_at_all(self):
        assert read_fallacy_target({}) is None


class TestSharedNotTwinned:
    """One owner, bound twice — a local re-declaration breaks identity."""

    def test_invoke_callables_binds_the_shared_resolver(self):
        from argumentation_analysis.orchestration import invoke_callables

        assert invoke_callables._ARG_ID_RE is ARG_ID_RE
        assert invoke_callables._FALLACY_TARGET_KEYS is FALLACY_TARGET_KEYS
        assert invoke_callables._read_fallacy_target is read_fallacy_target
        assert (
            invoke_callables._resolve_target_argument_index
            is resolve_target_argument_index
        )

    def test_service_binds_the_shared_resolver(self):
        from argumentation_analysis.services import semantic_index_service

        assert semantic_index_service.read_fallacy_target is read_fallacy_target
        assert (
            semantic_index_service.resolve_target_argument_index
            is resolve_target_argument_index
        )
        assert not hasattr(semantic_index_service, "_ARG_ID_RE")


class TestIntegerTargetTagsNothing:
    """End-to-end witness of the settled semantics: ``{"target_argument_id":
    1}`` associates no fallacy with any argument (the old service-side copy
    tagged the second argument 0-based; the shared resolver tags nothing)."""

    def test_int_target_leaves_all_arguments_untagged(self):
        service = SemanticIndexService()
        uploaded = []

        def mock_upload(name, text, source_type="text", tags=None):
            uploaded.append({"name": name, "tags": tags or {}})
            return f"doc_{len(uploaded)}"

        service.upload_document = mock_upload

        service.index_arguments(
            arguments=[
                {"text": "Climate change is caused by human activity"},
                {"text": "The earth is flat because the horizon looks flat"},
            ],
            source_name="test",
            fallacies=[{"target_argument_id": 1, "type": "ad_hominem"}],
        )
        assert uploaded
        for entry in uploaded:
            assert entry["tags"]["has_fallacy"] == "false"
