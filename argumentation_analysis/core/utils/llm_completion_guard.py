"""Reasoning-starved completion guard (#1929).

A reasoning model spends invisible reasoning tokens before emitting the
first character. When the completion budget is tighter than its reasoning
spend, the provider still answers HTTP 200 — with an EMPTY content and
``finish_reason == "length"``. No exception, no retry, no error trace: for
any caller that only checks the status code, the failure is
indistinguishable from success.

Measured on the two budget-pinning call sites (issue #1929, real prompts,
budget 200): a reasoning-heavy model burns 100 % of the envelope (192/192)
and renders 0 characters; the production default renders its answer but
spends 47-69 % of the envelope on reasoning first — the margin is thin, so
what makes the hole visible when a heavier turn or a chattier model crosses
it is this guard, not the budget value.

The discriminator is the finish reason, never the length: an empty answer
with ``finish_reason == "stop"`` is a legitimate empty answer and passes.
"""


class ReasoningStarvedError(RuntimeError):
    """The completion budget was consumed entirely by reasoning; content is empty."""


def assert_not_reasoning_starved(finish_reason, content, *, site):
    """Raise ReasoningStarvedError if the call was starved by its own budget.

    ``finish_reason`` accepts the raw provider string or the str-enum
    ``FinishReason`` carried by Semantic Kernel's ChatMessageContent — both
    compare equal to ``"length"``. ``content`` may be None.
    """
    if finish_reason == "length" and not (content or "").strip():
        raise ReasoningStarvedError(
            f"{site}: completion budget consumed entirely by reasoning — "
            "finish_reason='length' with empty content arrives as HTTP 200 "
            "(#1929); this is a failed call, not an empty answer"
        )
