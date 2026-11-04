"""#3375 — which family a model belongs to, and why the judge must differ.

The v1 panel (Epic #3374) compares the pipeline against a zero-shot arm of
the SAME model, and has that comparison judged by a reader of ANOTHER
family. "Another family" has to be a decision a program can make and a
reader can check, so it lives here as a small table rather than as a hope:

- the family is read from the model id's prefix (``gpt-`` → OpenAI,
  ``claude-`` → Anthropic, …);
- an id whose family is unknown **raises**. It is not guessed: a judge whose
  family cannot be established cannot be shown to differ from the pipeline's,
  and the whole point of the blind judge is that it is not the pipeline
  marking its own paper (the grid's opening line, ``GRILLE_JUGE_2841.md``).

Adding a model means adding one prefix here — deliberately a one-line
change, so that "the judge is another family" is never quietly assumed.
"""

from __future__ import annotations

from typing import Tuple

from argumentation_analysis.services.model_prices import bare_model_id

# id prefixes, longest first at match time so ``gpt-`` never swallows
# ``gpt-oss`` and a vendor rename cannot silently fall through.
_FAMILY_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("claude-", "anthropic"),
    ("gpt-", "openai"),
    ("chatgpt-", "openai"),
    ("o1-", "openai"),
    ("o3-", "openai"),
    ("o4-", "openai"),
    ("text-", "openai"),
    ("gemini-", "google"),
    ("gemma-", "google"),
    ("mistral-", "mistral"),
    ("mixtral-", "mistral"),
    ("ministral-", "mistral"),
    ("devstral-", "mistral"),
    ("qwen", "qwen"),
    ("glm-", "zhipu"),
    ("deepseek-", "deepseek"),
    ("llama-", "meta"),
    ("grok-", "xai"),
)


class UnknownModelFamily(ValueError):
    """The id carries no known family — refusing beats guessing (#3375)."""


def model_family(model_id: str) -> str:
    """Return the family of ``model_id``, or raise ``UnknownModelFamily``.

    The id is lowercased and stripped, so a provider that echoes its own
    casing (``GPT-5.6-LUNA``) resolves to the same row as the lowercase form.
    A routed id (``openai/gpt-5.6-luna``, the form OpenRouter records) is read
    through the price table's own ``bare_model_id``, so the family and the
    price of one call are read from one key and cannot disagree.
    """
    normalised = bare_model_id(model_id)
    if not normalised:
        raise UnknownModelFamily(
            "empty model id: the judge's family cannot be established, and a "
            "verdict from a model that cannot be shown to differ from the "
            "pipeline is not a blind judgement (#3375)"
        )
    # Longest prefix first — sorted HERE, not trusted from the table's
    # declaration order, so adding ``x-`` above ``x-long-`` cannot silently
    # shadow the longer row.
    for prefix, family in sorted(
        _FAMILY_PREFIXES, key=lambda row: len(row[0]), reverse=True
    ):
        if normalised.startswith(prefix):
            return family
    from argumentation_analysis.services.model_prices import PRICE_TABLE

    known = sorted({row.model_id for row in PRICE_TABLE})
    raise UnknownModelFamily(
        f"unknown model family for {model_id!r} — add its prefix to "
        f"argumentation_analysis/evaluation/model_family.py; the priced ids "
        f"are {known}. An unknown family cannot be shown to differ from the "
        f"pipeline's, so the judge would not be blind (#3375)."
    )


def assert_judge_differs(judge_model: str, pipeline_model: str) -> Tuple[str, str]:
    """Return ``(judge_family, pipeline_family)`` or raise ``ValueError``.

    Raised with the two families named: the caller prints why the run
    stopped, and a reader can check the two ids for themselves.
    """
    judge_family = model_family(judge_model)
    pipeline_family = model_family(pipeline_model)
    if judge_family == pipeline_family:
        raise ValueError(
            f"the judge {judge_model!r} and the pipeline {pipeline_model!r} "
            f"are both {judge_family} — a same-family judge marks the "
            f"pipeline's own paper, which the v1 bar forbids (#3374/#3375; "
            f"GRILLE_JUGE_2841.md opens on exactly this exclusion)"
        )
    return judge_family, pipeline_family
