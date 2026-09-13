"""Instance vocabulary of the encrypted corpus — derived, never listed (#2187).

``leak_patterns`` carries the CLASS half of rule 7: generic public vocabulary
(public figures, states, parties) that is safe to enumerate in a tracked file.
This module carries the INSTANCE half — the labels that map onto an encrypted
document of the census. Rule 7 forbids those in a tracked file, *including*
inside a detector's pattern list: "a detector that enumerates corpus
identifiers publishes the census the encryption protects". They are therefore
derived here, at run time, from the definitions decrypted in memory (rule 5),
and never written down.

Why a derivation rather than a salted fingerprint (#2187 arbitration): a
salted hash applies 1:1 to a document just as a name does — it makes reading
expensive, it does not remove the correspondence, and it buys a new failure
mode (a missing salt degrading silently into a detector that matches nothing).
Deriving dissolves the question instead: the tracked list carries class
vocabulary only, and instance coverage follows the census automatically, for
present *and future* sources. No reader has to judge an entry any more.

What counts as the document's identifying vocabulary
----------------------------------------------------
A census label is a natural-language title — ``<label> <type> <date>``,
``<label> - <title>``, ``<title> (<label>)``. Its identifying part is its
**capitalised** vocabulary: function words are lower case in French and
English alike, proper nouns and titles are not. The derivation yields, for
each ``source_name``: the whole name, plus every capitalised alphanumeric run
of four characters or more, case-folded.

The bias is deliberate, and it is the safe direction. A capitalised word
shared by several titles (``Discours``, ``Assemblée``) is redacted although it
identifies nothing on its own. Over-redaction costs a field of an export;
under-redaction is the privacy failure this discipline exists to prevent.

This module must stay import-light: the crypto/settings imports live inside
``load_instance_tokens`` so that importing it costs nothing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping

#: Shortest capitalised run kept as a candidate label token. Three-letter runs
#: are dominated by acronyms of the title vocabulary itself, which the class
#: list already covers; four keeps the proper nouns without the noise.
_MIN_TOKEN_LEN = 4

#: Runs of alphanumerics, Latin-1 Supplement and Latin Extended included so
#: accented French labels tokenise as single words rather than splitting.
_WORD_RUN = re.compile(r"[0-9A-Za-zÀ-ɏ]+")


class CorpusUnavailableError(RuntimeError):
    """The encrypted corpus could not be read.

    Raised instead of returning an empty set: a scrubber whose instance
    vocabulary collapsed to the class list would keep exporting while the
    redaction it promises is gone — the silent degradation the #2187
    arbitration explicitly rejects.
    """


def derive_instance_tokens(
    definitions: Iterable[Mapping[str, Any]],
) -> frozenset[str]:
    """Instance vocabulary of a corpus, from its already-decrypted definitions.

    Pure: no I/O, no settings, no key. Production feeds it the definitions
    ``load_instance_tokens`` just decrypted; a test feeds it its own — which
    keeps the mechanism identical on both sides without writing a single real
    label into a tracked file.
    """
    tokens: set[str] = set()
    for definition in definitions:
        name = str(definition.get("source_name") or "").strip()
        if not name:
            continue
        tokens.add(name.casefold())
        for match in _WORD_RUN.finditer(name):
            run = match.group(0)
            if len(run) < _MIN_TOKEN_LEN:
                continue
            if not run[0].isupper() or not any(c.isalpha() for c in run):
                continue
            tokens.add(run.casefold())
    return frozenset(tokens)


def load_instance_tokens() -> frozenset[str]:
    """Derive the instance vocabulary from the encrypted corpus (rule 5).

    The decrypted definitions never leave memory; only the derived tokens are
    returned. Fails loud on every path that would otherwise yield a silently
    empty vocabulary.
    """
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.utils.crypto_utils import load_encryption_key

    key = load_encryption_key()
    if not key:
        raise CorpusUnavailableError(
            "No passphrase available (neither an argument nor settings.passphrase): "
            "the corpus's instance vocabulary cannot be derived. Refusing to "
            "return an empty set — the scrubber's instance half would be gone "
            "while it kept exporting (#2187)."
        )

    config_file = Path(settings.config_file_enc)
    if not config_file.exists():
        raise CorpusUnavailableError(
            f"Encrypted corpus not found at {config_file}: instance vocabulary "
            "cannot be derived (#2187)."
        )

    definitions = load_extract_definitions(
        config_file=config_file,
        b64_derived_key=key.decode("utf-8"),
        raise_on_decrypt_error=True,
    )
    if not definitions:
        raise CorpusUnavailableError(
            f"Decryption of {config_file.name} yielded no definition: instance "
            "vocabulary cannot be derived (#2187)."
        )

    tokens = derive_instance_tokens(definitions)
    if not tokens:
        raise CorpusUnavailableError(
            f"{len(definitions)} definitions loaded but none carried a "
            "source_name: instance vocabulary cannot be derived (#2187)."
        )
    return tokens
