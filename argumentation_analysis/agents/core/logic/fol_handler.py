import jpype
import logging
import asyncio
import re
import time

# La configuration du logging (appel à setup_logging()) est supposée être faite globalement.
from argumentation_analysis.core.utils.logging_utils import setup_logging
from .tweety_initializer import TweetyInitializer
from argumentation_analysis.core.prover9_runner import (
    PROVER9_EXECUTABLE,
    SolverInputDefect,
    run_prover9,
)
from argumentation_analysis.core.mace4_runner import (
    MACE4_EXECUTABLE,
    interpret_mace4_output,
    run_mace4,
)
from argumentation_analysis.core.config import settings, SolverChoice

setup_logging()
logger = logging.getLogger(__name__)


def _get_eprover_path() -> "str | None":
    """Return the detected EProver binary path, or None if not wired.

    Reads the module-level registry populated by
    ``jvm_setup._configure_external_tools``. Centralised here so the FOL handler
    does not duplicate the detection logic and the wiring is testable in
    isolation (#1196).
    """
    try:
        from argumentation_analysis.core.jvm_setup import EXTERNAL_TOOL_PATHS

        return EXTERNAL_TOOL_PATHS.get("eprover")
    except Exception:  # pragma: no cover - import guard
        return None


# #1441: bare-constant boolean sanitization for FOL formulas. Tweety's FOL BNF
# (``tweety_fol_bnf.md``, firsthand-confirmed vs FolParser.java) uses ``+``/``-``
# for Top/Bottom — a bare ``T``/``F`` emitted by an LLM is an undeclared atom and
# raises ``ParserException: Unrecognized formula type 'T'`` (ATT-3 corpus C
# firsthand finding). The map targets standalone uppercase ``T``/``F`` tokens only
# (word boundaries), so ``Table``, ``T1``, and lowercase ``t`` survive untouched.
_FOL_BOOL_CONSTANT_RE = re.compile(r"(?<![A-Za-z0-9_])([TF])(?![A-Za-z0-9_])")
_FOL_BOOL_MAP = {"T": "+", "F": "-"}


def _sanitize_fol_bool_constants(formula: str) -> str:
    """Map bare ``T``/``F`` to Tweety Top/Bottom ``+``/``-`` (#1441).

    Idempotent and conservative: only standalone uppercase tokens are mapped,
    so identifiers (``Table``, ``T1``) and lowercase (``t``) pass through.
    """
    if "T" not in formula and "F" not in formula:
        return formula
    return _FOL_BOOL_CONSTANT_RE.sub(
        lambda m: _FOL_BOOL_MAP.get(m.group(1), m.group(1)), formula
    )


# Cache: eprover binary path -> bool (delivery contract verified on this platform).
# The sentinel is a one-off subprocess per binary, not per-query overhead.
_EPROVER_DELIVERY_RELIABLE: "dict[str, bool]" = {}


def _eprover_delivery_is_reliable(reasoner, eprover_path: str) -> bool:
    """Anti-théâtre sentinel guard for the Tweety->EProver delivery contract (#1019, #1204).

    Tweety's ``EFOLReasoner`` builds the command ``<eprover> --auto-schedule
    --tptp3-format <file>`` and runs it through ``NativeShell`` via
    ``Runtime.exec(String)`` (the fragile, non-portable single-String overload
    that re-tokenises on whitespace). On some platform/E-version combinations
    (firsthand-observed on Linux with E 3.x, #1204) the problem file never
    reaches the binary — E reads empty input, proves the *empty* theory
    ``Satisfiable`` and a genuinely **inconsistent** KB is reported *consistent*.
    That is a fabricated verdict, exactly the failure #1019 forbids.

    Before trusting any eprover verdict, run a known-inconsistent sentinel
    ``{P(a), !P(a)}`` through the SAME reasoner. If the contradiction is not
    detected, the delivery is broken here and eprover must not be trusted — the
    caller raises so ``fol_check_consistency`` falls back to the in-JVM Tweety
    reasoner instead of serving a fabricated answer. Result cached per path.

    Returns True iff the sentinel is correctly reported inconsistent.
    """
    cached = _EPROVER_DELIVERY_RELIABLE.get(eprover_path)
    if cached is not None:
        return cached
    reliable = False
    try:
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        sentinel = FolParser().parseBeliefBase(
            "human = {a}\ntype(P(human))\n\nP(a)\n!P(a)\n"
        )
        probe_parser = FolParser()
        probe_parser.setSignature(sentinel.getMinimalSignature())
        contradiction = probe_parser.parseFormula("-")
        # query returns True iff the KB entails the contradiction (= inconsistent).
        reliable = bool(reasoner.query(sentinel, contradiction))
    except Exception as e:  # parser/JVM hiccup -> unreliable, fail loud
        logger.error(
            f"EProver sentinel self-check raised ({e}); treating eprover as unreliable."
        )
        reliable = False
    _EPROVER_DELIVERY_RELIABLE[eprover_path] = reliable
    if not reliable:
        logger.error(
            "EProver sentinel self-check FAILED: known-inconsistent {P(a),!P(a)} "
            "was not reported inconsistent — the problem is not reaching the solver "
            "on this platform (Tweety<->E delivery contract broken, #1204). EProver "
            "verdicts cannot be trusted here; falling back to the in-JVM reasoner."
        )
    return reliable


# --------------------------------------------------------------------------- #
# Mace4 (LADR model-finder) — FP-19 #1243. The CONSISTENCY side of the FOL
# multi-prover comparison: it proves consistent by exhibiting a finite model
# (sound), complementing EProver/Prover9's refutation (which proves inconsistent).
# --------------------------------------------------------------------------- #


def _belief_set_to_ladr_assumptions(belief_set) -> str:
    """Build a LADR ``formulas(assumptions). … end_of_list.`` block from a Tweety
    ``FolBeliefSet``.

    Iterates the belief set's INDIVIDUAL formulas (a ``FolBeliefSet`` is a Java
    ``Collection``) and writes each from its structure (``_ladr_text``) as a
    LADR clause terminated by ``.``.
    This deliberately avoids ``belief_set.toString()`` — that renders the set as
    ``{ f1, f2 }`` (brace + comma), which Mace4/Prover9 reject as "Set parsing is
    not available" (the reason the legacy Prover9 path never genuinely decided
    and always fell back). Mace4 searches for a model of these assumptions.
    """
    body = "\n".join(_ladr_text(formula) + "." for formula in belief_set)
    # #2482: LADR reads a free symbol starting with ``u``-``z`` as a variable,
    # so the constant in ``Red(zone)`` meant "everything is red" and a
    # consistent KB had no model. Prolog style is Tweety's own convention
    # (constants start lowercase or with a digit, variables uppercase).
    return (
        "set(prolog_style_variables).\n"
        f"formulas(assumptions).\n{body}\nend_of_list.\n"
    )


def _prover9_input(belief_set, goal=None) -> str:
    """Prover9 input for a Tweety ``FolBeliefSet`` (#2482).

    The one builder every Prover9 caller uses: the belief set's formulas as
    LADR assumptions (the text Mace4 reads), and one goal, a parsed Tweety
    formula written the same way. Without a goal it is ``$F``: a
    proof of falsehood from the assumptions means they are inconsistent.
    """
    if goal is None:
        goal_ladr = "$F"
    else:
        goal_ladr = _ladr_text(goal)
    return (
        f"{_belief_set_to_ladr_assumptions(belief_set)}"
        f"formulas(goals).\n{goal_ladr}.\nend_of_list.\n"
    )


# Prover9's last lines: how many proofs it found, and why it stopped.
_PROVER9_PROOFS_RE = re.compile(r"^Exiting with (\d+) proofs?\.", re.MULTILINE)
_PROVER9_EXIT_RE = re.compile(r"^Process \d+ exit \((\w+)\)", re.MULTILINE)


def _prover9_proved(output: str) -> "bool | None":
    """``True`` when Prover9 proved its goal, ``False`` when its search ran out
    of clauses without a proof, ``None`` when it stopped on neither (a resource
    limit): Prover9 then decided nothing.

    Read from the proof count and the exit reason (#2506). ``THEOREM PROVED``
    is printed only when the count reaches ``max_proofs``, which
    ``auto_denials`` can raise to 2 (measured with a negative clause of two
    literals beside the goal's denial): the one proof is found, the search for
    a second runs out, and the output ends on ``SEARCH FAILED``. That marker
    is printed on every exit short of ``max_proofs``, a resource limit
    included.
    """
    proofs = _PROVER9_PROOFS_RE.search(output)
    if proofs is not None and int(proofs.group(1)) > 0:
        return True
    exit_reason = _PROVER9_EXIT_RE.search(output)
    if exit_reason is not None and exit_reason.group(1) == "sos_empty":
        return False
    return None


# Cache: Mace4 binary path -> bool (delivery contract verified on this platform).
_MACE4_DELIVERY_RELIABLE: "dict[str, bool]" = {}


def _mace4_delivery_is_reliable() -> bool:
    """Anti-théâtre sentinel for the Mace4 delivery contract (#1019, generalizes
    ``_eprover_delivery_is_reliable``).

    A model-finder cannot prove inconsistency, so its sentinel exercises its
    SOUND capability instead: a known-consistent KB ``{ptest(a)}`` MUST yield a
    finite model. If Mace4 fails to find a model for a trivially-satisfiable KB,
    the input is not reaching the binary (or the binary is broken) — Mace4 must
    not be trusted, and the caller falls back / contributes ``None`` rather than
    serving a possibly-degraded verdict. Result cached per binary path.
    """
    key = str(MACE4_EXECUTABLE)
    cached = _MACE4_DELIVERY_RELIABLE.get(key)
    if cached is not None:
        return cached
    reliable = False
    try:
        out = run_mace4("formulas(assumptions).\nptest(a).\nend_of_list.\n")
        verdict, _ = interpret_mace4_output(out)
        reliable = verdict is True
    except Exception as e:  # binary/timeout hiccup -> unreliable, fail loud
        logger.error(
            f"Mace4 sentinel self-check raised ({e}); treating Mace4 as unreliable."
        )
        reliable = False
    _MACE4_DELIVERY_RELIABLE[key] = reliable
    if not reliable:
        logger.error(
            "Mace4 sentinel self-check FAILED: known-consistent {ptest(a)} did not "
            "yield a finite model — the problem is not reaching Mace4 (delivery "
            "broken). Mace4 verdicts cannot be trusted here."
        )
    return reliable


# #2494: above this many ground atoms the in-JVM reasoner's enumeration of every
# Herbrand interpretation (2^atoms) is not attempted with witnesses (#1192).
# Measured on myia-ai-01: 18 atoms 9 s, 20 atoms 56 s.
_IN_JVM_MAX_ATOMS = 16


def _fol_class(name: str):
    return jpype.JClass("org.tweetyproject.logics.fol.syntax." + name)


def _commons_class(name: str):
    return jpype.JClass("org.tweetyproject.logics.commons.syntax." + name)


def _positive_existentials(java_belief_set) -> "tuple[list, bool]":
    """The sorts of the variables quantified existentially in effect, and
    whether an inconsistency found over one witness per variable is exact
    (#2494).

    A quantifier's effect is read from its polarity, counted here rather than
    taken from Tweety's ``toNnf()``, which leaves a negation over an
    implication. An ``exists`` under an even number of negations (a premise
    counts as one), or a ``forall`` under an odd number, needs a witness; a
    side of an equivalence is read in both polarities. The witnesses are the
    Skolem constants of those under no universal in effect; one under a
    universal needs a Skolem function, which a finite set of constants does not
    replace. Equality, or a node this walk does not know, makes the answer
    inexact.
    """
    exists_cls = _fol_class("ExistsQuantifiedFormula")
    forall_cls = _fol_class("ForallQuantifiedFormula")
    junction_cls = (_fol_class("Conjunction"), _fol_class("Disjunction"))
    negation_cls = _fol_class("Negation")
    implication_cls = _fol_class("Implication")
    equivalence_cls = _fol_class("Equivalence")
    atom_cls = _fol_class("FolAtom")
    special_cls = (_fol_class("Tautology"), _fol_class("Contradiction"))
    sorts: list = []
    exact = [True]

    def walk(formula, positive: bool, under_forall: bool) -> None:
        if isinstance(formula, (exists_cls, forall_cls)):
            existential = isinstance(formula, exists_cls) == positive
            if existential:
                for variable in formula.getQuantifierVariables():
                    sorts.append(variable.getSort())
                if under_forall:
                    exact[0] = False
            walk(formula.getFormula(), positive, under_forall or not existential)
        elif isinstance(formula, junction_cls):
            for sub in formula.getFormulas():
                walk(sub, positive, under_forall)
        elif isinstance(formula, negation_cls):
            walk(formula.getFormula(), not positive, under_forall)
        elif isinstance(formula, implication_cls):
            pair = formula.getFormulas()
            walk(pair.getFirst(), not positive, under_forall)
            walk(pair.getSecond(), positive, under_forall)
        elif isinstance(formula, equivalence_cls):
            pair = formula.getFormulas()
            for side in (pair.getFirst(), pair.getSecond()):
                walk(side, True, under_forall)
                walk(side, False, under_forall)
        elif isinstance(formula, atom_cls):
            if not str(formula.getPredicate().getName())[:1].isalpha():
                exact[0] = False  # equality and other built-ins
        elif not isinstance(formula, special_cls):
            exact[0] = False

    for formula in java_belief_set:
        walk(formula, True, False)
    return sorts, exact[0]


class UnwritableFormula(SolverInputDefect):
    """The writer has no text for a node of the formula (#2504). The parser
    gives none of these (an uppercase name parses as a variable, and equality
    is refused), so the formula was built in code: a defect of our input, like
    one Prover9 refuses."""


def _ladr_term(term) -> str:
    """``term`` in LADR, which reads a symbol by its first letter under
    Prolog-style variables (#2482). Tweety refuses a variable that does not
    start uppercase. A constant built in code may start uppercase, and LADR
    would read it as a variable, so it is refused."""
    name = str(term)
    first = name[:1]
    if isinstance(term, _commons_class("Variable")):
        return name
    if isinstance(term, _commons_class("Constant")) and (
        first.islower() or first.isdigit()
    ):
        return name
    raise UnwritableFormula(f"no LADR text for the term {name}")


# The two syntaxes a formula is written in (#2494, #2504): the Tweety parser's,
# and LADR's, which Prover9 and Mace4 read. LADR has no exclusive disjunction,
# and it reads a symbol that starts uppercase in a formula's place as a
# variable (``Bad`` alone was refused), so its predicates carry a prefix.
_TWEETY_SYNTAX = {
    "not": "!",
    "and": " && ",
    "or": " || ",
    "xor": " ^^ ",
    "implies": " => ",
    "iff": " <=> ",
    "forall": "forall {}: ({})",
    "exists": "exists {}: ({})",
    "true": "+",
    "false": "-",
    "predicate": "{}",
    "term": str,
}
_LADR_SYNTAX = {
    "not": "-",
    "and": " & ",
    "or": " | ",
    "xor": None,
    "implies": " -> ",
    "iff": " <-> ",
    "forall": "all {} ({})",
    "exists": "exists {} ({})",
    "true": "$T",
    "false": "$F",
    "predicate": "p_{}",
    "term": _ladr_term,
}


def _formula_text(formula, syntax: dict) -> str:
    """``formula`` written from its structure in ``syntax``, every sub-formula
    parenthesised (#2494, #2504).

    ``str()`` drops the parentheses a negation needs: ``!(Man(a) && Man(b))``
    prints as ``!Man(a)&&Man(b)``, which the Tweety parser and LADR both read
    as another formula, and a negated quantifier prints as text the parser
    refuses. A node this writer does not know raises ``ValueError``.
    """
    if isinstance(formula, _fol_class("Negation")):
        return f"{syntax['not']}({_formula_text(formula.getFormula(), syntax)})"
    for name, key in (
        ("Conjunction", "and"),
        ("Disjunction", "or"),
        ("ExclusiveDisjunction", "xor"),
    ):
        if isinstance(formula, _fol_class(name)):
            parts = [_formula_text(sub, syntax) for sub in formula.getFormulas()]
            if syntax[key] is None:
                # Tweety's exclusive disjunction holds when an odd number of
                # its operands do, which a chain of non-equivalences writes.
                text = parts[0]
                for part in parts[1:]:
                    text = f"{syntax['not']}(({text}){syntax['iff']}({part}))"
                return text
            return "(" + syntax[key].join(f"({part})" for part in parts) + ")"
    for name, key in (("Implication", "implies"), ("Equivalence", "iff")):
        if isinstance(formula, _fol_class(name)):
            pair = formula.getFormulas()
            first = _formula_text(pair.getFirst(), syntax)
            second = _formula_text(pair.getSecond(), syntax)
            return f"(({first}){syntax[key]}({second}))"
    for name, key in (
        ("ExistsQuantifiedFormula", "exists"),
        ("ForallQuantifiedFormula", "forall"),
    ):
        if isinstance(formula, _fol_class(name)):
            text = _formula_text(formula.getFormula(), syntax)
            for variable in formula.getQuantifierVariables():
                text = syntax[key].format(syntax["term"](variable), text)
            return text
    if isinstance(formula, _fol_class("FolAtom")):
        name = str(formula.getPredicate().getName())
        if not name[:1].isalpha():
            raise UnwritableFormula(f"no text for the built-in predicate {name}")
        args = [syntax["term"](term) for term in formula.getArguments()]
        name = syntax["predicate"].format(name)
        return f"{name}({', '.join(args)})" if args else name
    if isinstance(formula, _fol_class("Tautology")):
        return syntax["true"]
    if isinstance(formula, _fol_class("Contradiction")):
        return syntax["false"]
    raise UnwritableFormula(f"no text for {formula.getClass().getName()}")


def _tweety_text(formula) -> str:
    """``formula`` in the syntax the Tweety parser reads (#2494)."""
    return _formula_text(formula, _TWEETY_SYNTAX)


def _ladr_text(formula) -> str:
    """``formula`` in LADR, the input of Prover9 and Mace4 (#2504)."""
    return _formula_text(formula, _LADR_SYNTAX)


def _in_jvm_consistency(reasoner, java_belief_set) -> "tuple[bool | None, str]":
    """``SimpleFolReasoner``'s consistency verdict, read for what it decides
    (#2494).

    The reasoner's quantifiers range over the declared sorts, but its Herbrand
    base holds only the constants that appear in a formula or in the query: an
    atom over any other declared constant is always false. And its domain is
    closed: a set that needs an individual nobody named reads inconsistent.

    So the check runs on a copy of the set whose sorts carry one fresh witness
    per positive existential variable, against a contradiction that names every
    constant, which puts them all in the Herbrand base. "Consistent" is then a
    finite model, so it is sound. "Inconsistent" is exact when no positive
    existential sits under a universal (the witnesses are its Skolem
    constants); otherwise it reads ``None``. Nothing is fabricated: a copy that
    cannot be built, or would exceed ``_IN_JVM_MAX_ATOMS``, leaves the plain
    check, whose "inconsistent" also reads ``None``.
    """
    parser_cls = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
    constant_cls = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")
    string_reader = jpype.JClass("java.io.StringReader")
    witness_sorts, exact = _positive_existentials(java_belief_set)
    signature = java_belief_set.getSignature()

    sort_constants: "dict[str, list[str]]" = {}
    for sort in signature.getSorts():
        sort_constants[str(sort.getName())] = sorted(
            str(c.get()) for c in sort.getTerms(constant_cls)
        )
    taken = {c for names in sort_constants.values() for c in names}
    formula_constants = {
        str(c.get()) for c in java_belief_set.getMinimalSignature().getConstants()
    }
    declared_only = taken - formula_constants
    witnesses = 0
    for sort in witness_sorts:
        index = 1
        while f"witness{index}" in taken:
            index += 1
        taken.add(f"witness{index}")
        sort_constants.setdefault(str(sort.getName()), []).append(f"witness{index}")
        witnesses += 1

    predicates = []
    for predicate in signature.getPredicates():
        name = str(predicate.getName())
        if not name[:1].isalpha():
            continue  # equality and other built-ins are not declared
        predicates.append(
            (name, [str(s.getName()) for s in predicate.getArgumentTypes()])
        )

    # One atom per constant, so that the contradiction's signature, which the
    # reasoner adds to the Herbrand base, names every constant (#2494).
    atoms: "list[str]" = []
    covered: "set[str]" = set()
    ground_atoms = 0
    for name, arg_sorts in predicates:
        pools = [sort_constants.get(s, []) for s in arg_sorts]
        count = 1
        for pool in pools:
            count *= len(pool)
        ground_atoms += count
        if not arg_sorts or any(not pool for pool in pools):
            continue
        for position, pool in enumerate(pools):
            for constant in pool:
                if constant in covered:
                    continue
                args = [p[0] for p in pools]
                args[position] = constant
                atoms.append(f"{name}({', '.join(args)})")
                covered.add(constant)

    def plain() -> "tuple[bool | None, str]":
        contradiction = parser_cls()
        contradiction.setSignature(java_belief_set.getMinimalSignature())
        inconsistent = bool(
            reasoner.query(java_belief_set, contradiction.parseFormula("-"))
        )
        if not inconsistent:
            return True, "consistent (a model over the declared constants)"
        if exact and not witnesses and not declared_only:
            # No positive existential, and every declared constant is in the
            # Herbrand base: the set is universal over its own constants.
            return False, "inconsistent (no model over the declared constants)"
        return None, (
            "no model over the formulas' constants alone; a witness or a "
            "declared-only constant is missing from that domain, so this does "
            "not decide inconsistency"
        )

    if not witnesses and not declared_only:
        # The plain check already covers the whole domain, at its usual cost.
        return plain()
    if ground_atoms > _IN_JVM_MAX_ATOMS or any(
        not names for names in sort_constants.values()
    ):
        return plain()

    lines = [
        f"{sort} = {{{', '.join(names)}}}" for sort, names in sort_constants.items()
    ]
    lines += [
        f"type({name}({', '.join(arg_sorts)}))" if arg_sorts else f"type({name})"
        for name, arg_sorts in predicates
    ]
    try:
        lines += [_tweety_text(formula) for formula in java_belief_set]
        parser = parser_cls()
        widened = parser.parseBeliefBase(string_reader("\n".join(lines)))
        widened.setSignature(parser.getSignature())
        query_parser = parser_cls()
        query_parser.setSignature(parser.getSignature())
        query = query_parser.parseFormula(
            " || ".join(f"({a} && !{a})" for a in atoms) if atoms else "-"
        )
    except Exception as e:  # the copy is ours: say so, then read the plain check
        logger.warning(
            f"#2494: the witnessed copy of the belief set could not be built ({e}); "
            "the plain in-JVM check answers, and its 'inconsistent' reads None."
        )
        return plain()

    inconsistent = bool(reasoner.query(widened, query))
    domain = f"the declared constants and {witnesses} witness(es)"
    if not inconsistent:
        return True, f"consistent (a model over {domain})"
    if exact:
        return False, f"inconsistent (no model over {domain}, which is exact here)"
    return None, (
        f"no model over {domain}, but an existential under a universal (or "
        "equality) makes that domain insufficient; no verdict"
    )


def _in_jvm_entailment(
    reasoner, java_belief_set, query_formula
) -> "tuple[bool | None, str]":
    """Whether ``java_belief_set`` entails ``query_formula``, read through
    ``_in_jvm_consistency`` (#2502).

    Asked directly, ``SimpleFolReasoner`` answers over the same split, closed
    domain as its consistency check (#2494), so "entailed" was not sound:
    ``Man(s)`` entailed ``forall X: (Man(X))``. Entailment is the
    inconsistency of the set plus the query's negation, and that check already
    says what its domain decides: a model of it is a real countermodel ("not
    entailed"), an exact inconsistency is "entailed", anything else reads
    ``None``.
    """
    syntax = "org.tweetyproject.logics.fol.syntax."
    refutation = jpype.JClass(syntax + "FolBeliefSet")()
    for formula in java_belief_set:
        refutation.add(formula)
    refutation.add(jpype.JClass(syntax + "Negation")(query_formula))
    consistent, note = _in_jvm_consistency(reasoner, refutation)
    # The verdict word ends the message, as it did before (#2447 readers).
    if consistent is True:
        return False, f"the set and the query's negation are {note}, so not entailed"
    if consistent is False:
        return True, f"the set and the query's negation are {note}, so entailed"
    return None, f"{note}; no verdict on entailment"


class FOLHandler:
    """
    Handles First-Order Logic (FOL) operations using either TweetyProject or Prover9,
    based on the application's configuration.
    """

    def __init__(self, initializer_instance: TweetyInitializer = None):
        """
        Initializes the FOLHandler.
        The initializer_instance is optional and only required for the Tweety solver path.
        """
        self.logger = logging.getLogger(__name__)
        self._initializer_instance = initializer_instance

        # Le parser et autres composants Tweety ne sont chargés que si nécessaire.
        self._fol_parser = None
        if settings.solver == SolverChoice.TWEETY:
            # La vérification de _initializer_instance est maintenant faite dans chaque méthode tweety
            if self._initializer_instance:
                self._fol_parser = self._initializer_instance.get_fol_parser()
                if self._fol_parser is None:
                    logger.error(
                        "FOL Parser not initialized. Ensure TweetyBridge calls TweetyInitializer first."
                    )
                    raise RuntimeError(
                        "FOLHandler initialized before TweetyInitializer completed FOL setup."
                    )

    def parse_fol_formula(self, formula_str: str, custom_parser=None):
        """
        Parses a single FOL formula string.
        If a custom_parser (with a specific signature) is provided, it uses it.
        Otherwise, it uses the default FOL parser.
        """
        if not isinstance(formula_str, str):
            raise TypeError("Input formula must be a string.")

        # #1441: sanitize LLM-emitted boolean constants BEFORE parsing. Tweety's
        # FOL grammar (firsthand-confirmed BNF, ``tweety_fol_bnf.md``) uses
        # ``+``/``-`` for Top/Bottom, NOT ``T``/``F`` — so a formula like
        # ``forall X: (P(X) => T)`` raises ``ParserException`` and the formula is
        # lost (ATT-3 firsthand finding, corpus C). Mapping bare ``T``/``F``
        # tokens (word-boundary, uppercase only) to ``+``/``-`` recovers them.
        # ``Table``/``T1``/lowercase ``t`` are untouched. Applied to the formula
        # string only (predicate declarations go through the Java ``Predicate``
        # API, unaffected), and the substitution is logged when it fires
        # (visible, not silent — anti-théâtre #1019 fail-loud).
        sanitized = _sanitize_fol_bool_constants(formula_str)
        if sanitized != formula_str:
            logger.warning(
                "FOL formula boolean constants sanitized (T->+, F->-) "
                "#1441: %r -> %r",
                formula_str,
                sanitized,
            )
        formula_str = sanitized

        parser_to_use = custom_parser if custom_parser else self._fol_parser

        logger.debug(f"Attempting to parse FOL formula: {formula_str}")
        try:
            java_formula_str = jpype.JClass("java.lang.String")(formula_str)
            fol_formula = parser_to_use.parseFormula(java_formula_str)
            logger.info(
                f"Successfully parsed FOL formula: {formula_str} -> {fol_formula}"
            )
            return fol_formula
        except jpype.JException as e:
            logger.error(
                f"JPype JException parsing FOL formula '{formula_str}': {e.getMessage()}",
                exc_info=True,
            )
            raise ValueError(
                f"Error parsing FOL formula '{formula_str}': {e.getMessage()}"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error parsing FOL formula '{formula_str}': {e}",
                exc_info=True,
            )
            raise

    def create_belief_set_from_string(self, tweety_syntax: str):
        """
        Crée un FolBeliefSet directement à partir d'une chaîne de caractères
        utilisant la syntaxe native de Tweety.
        C'est la nouvelle approche privilégiée.

        :param tweety_syntax: Une chaîne contenant la base de connaissances complète.
        :return: Un objet FolBeliefSet de jpype.
        """
        logger.info(
            "Parsing de la base de connaissances FOL à partir de la syntaxe native."
        )
        StringReader = jpype.JClass("java.io.StringReader")
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")

        try:
            # CRUCIAL : Créer une instance de parser locale et isolée pour chaque appel.
            # Cela empêche la contamination de la signature entre les tests ou les appels.
            # L'instance partagée self._fol_parser conserve son état, ce qui cause des erreurs
            # de "redéclaration" lors d'appels successifs avec des données similaires.
            local_parser = FolParser()
            reader = StringReader(tweety_syntax)
            belief_set = local_parser.parseBeliefBase(reader)
            # The parsed belief set's signature holds only the symbols its
            # formulas use: a constant declared in a sort and used in no formula
            # is dropped, so a later query on it fails to parse (#2447). The
            # parser's signature is the declared one.
            belief_set.setSignature(local_parser.getSignature())
            logger.info(
                f"Parsing réussi avec un parser local. {belief_set.size()} formules chargées."
            )
            return belief_set
        except jpype.JException as e:
            # Il est crucial de remonter l'exception de parsing pour le feedback au LLM.
            self.logger.error(
                f"Erreur de parsing dans Tweety: {e.getMessage()}", exc_info=True
            )
            raise ValueError(f"Erreur de parsing Tweety: {e.getMessage()}") from e

    def create_belief_set_programmatically(self, builder_plugin_data: dict):
        """
        Crée un FolBeliefSet Java en mémoire à partir des données accumulées
        par le BeliefSetBuilderPlugin.
        C'est la nouvelle approche robuste qui contourne les bizarreries du
        parseur de fichier .fologic.
        """
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            BeliefSetBuilderPlugin,
        )

        sorts_data = builder_plugin_data.get("_sorts", {})
        predicates_data = builder_plugin_data.get("_predicates", {})
        formulas = builder_plugin_data.get("_formulas", [])

        FolSignature = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolSignature")
        FolBeliefSet = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
        Sort = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
        Constant = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")
        Predicate = jpype.JClass("org.tweetyproject.logics.commons.syntax.Predicate")
        String = jpype.JClass("java.lang.String")
        ArrayList = jpype.JClass("java.util.ArrayList")

        import re

        signature = FolSignature()
        sorts_map = {}  # Python-side mapping from name to Java Sort object

        # Étape 1: Collecter tous les sorts, constantes, et prédicats (déclarés et défensifs) en Python d'abord.

        # 1a. Collecter les prédicats déclarés par le LLM.
        # On fait une copie pour pouvoir la modifier sans affecter l'original.
        final_predicates_data = dict(predicates_data)

        # 1b. Scan défensif pour trouver les prédicats utilisés mais non déclarés.
        for formula_str in formulas:
            potential_preds = re.findall(r"([a-zA-Z][a-zA-Z0-9_]*)\(", formula_str)
            for pred_name in potential_preds:
                if pred_name not in final_predicates_data:
                    self.logger.warning(
                        f"Prédicat '{pred_name}' utilisé mais non déclaré. Ajout défensif."
                    )
                    # Estimation de l'arité
                    try:
                        inner_content_match = re.search(
                            re.escape(pred_name) + r"\((.*?)\)", formula_str
                        )
                        if inner_content_match:
                            inner_content = inner_content_match.group(1)
                            arity = inner_content.count(",") + 1 if inner_content else 0
                        else:
                            arity = 0  # Cas comme 'pred()'.
                    except Exception:
                        arity = 1  # Fallback sûr.

                    # Stratégie : tout prédicat non déclaré est de type (thing, thing, ...)
                    thing_sort_name = "thing"
                    final_predicates_data[pred_name] = [thing_sort_name] * arity

                    # S'assurer que 'thing' est bien dans la liste des sorts à créer.
                    if thing_sort_name not in sorts_data:
                        sorts_data[thing_sort_name] = []

        # Étape 2: Construire la signature Java complète en une seule passe.

        # 2a. Créer et ajouter tous les sorts.
        for sort_name in sorts_data.keys():
            try:
                java_sort = Sort(String(sort_name))
                signature.add(java_sort)
                sorts_map[sort_name] = java_sort
                self.logger.debug(f"Sort ajouté par programmation : {sort_name}")
            except jpype.JException as e:
                raise ValueError(
                    f"Échec de la création du sort Java '{sort_name}': {e.getMessage()}"
                ) from e

        # 2b. Créer et ajouter les constantes.
        for sort_name, constants_list in sorts_data.items():
            parent_sort = sorts_map.get(sort_name)
            if parent_sort:
                for const_name in constants_list:
                    try:
                        java_constant = Constant(String(const_name), parent_sort)
                        signature.add(java_constant)
                        self.logger.debug(
                            f"Constante ajoutée: {const_name} de type {sort_name}"
                        )
                    except jpype.JException as e:
                        raise ValueError(
                            f"Échec de la création de la constante '{const_name}': {e.getMessage()}"
                        ) from e

        # 2c. Créer et ajouter la liste COMPLÈTE des prédicats.
        for pred_name, arg_sort_names in final_predicates_data.items():
            java_arg_sorts = ArrayList()
            for arg_sort_name in arg_sort_names:
                java_sort = sorts_map.get(arg_sort_name)
                if not java_sort:
                    raise ValueError(
                        f"Incohérence: Le sort '{arg_sort_name}' du prédicat '{pred_name}' n'a pas été trouvé."
                    )
                java_arg_sorts.add(java_sort)

            try:
                java_predicate = Predicate(String(pred_name), java_arg_sorts)
                signature.add(java_predicate)
                self.logger.debug(
                    f"Prédicat ajouté: {pred_name} avec args {arg_sort_names}"
                )
            except jpype.JException as e:
                raise ValueError(
                    f"Échec de la création du prédicat '{pred_name}': {e.getMessage()}"
                ) from e

        # Étape 3: Créer le parser avec la signature finale et l'utiliser pour parser les formules.
        belief_set = FolBeliefSet()
        belief_set.setSignature(signature)

        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        parser = FolParser()
        parser.setSignature(signature)

        for formula_str in formulas:
            try:
                parsed_formula = self.parse_fol_formula(
                    formula_str, custom_parser=parser
                )
                if parsed_formula:
                    belief_set.add(parsed_formula)
                    self.logger.debug(f"Formule ajoutée: {formula_str}")
                else:
                    self.logger.warning(
                        f"Le parsing de '{formula_str}' a retourné None."
                    )
            except ValueError as e:
                self.logger.error(
                    f"Échec final du parsing de '{formula_str}' avec la signature construite : {e}"
                )
                raise e

        self.logger.info(
            f"Base de connaissances FOL créée par programmation avec {belief_set.size()} formules."
        )
        return belief_set, signature

    async def fol_check_consistency(self, belief_set):
        """
        Checks if an FOL knowledge base is consistent using the configured solver.

        When the configured external solver (eprover/prover9) is unavailable
        (binary absent, RuntimeError), falls back to the in-JVM Tweety FOL
        reasoner — mirroring the modal pattern (modal_handler.py:36-48).
        Returns a ``solver_fallback`` flag in the result so callers can track
        degradation.
        """
        self.logger.debug(
            f"Performing FOL consistency check with solver: {settings.solver.value}"
        )
        if settings.solver == SolverChoice.PROVER9:
            try:
                return await self._fol_check_consistency_with_prover9(belief_set)
            except SolverInputDefect:
                # #2489: a refused input is the builder's defect, not an
                # unavailable solver.
                raise
            except RuntimeError as e:
                self.logger.warning(
                    f"Prover9 unavailable ({e}), falling back to Tweety FOL reasoner"
                )
                return await self._fol_check_consistency_with_tweety_fallback(
                    belief_set
                )
        elif settings.solver == SolverChoice.EPROVER:
            try:
                return await self._fol_check_consistency_with_eprover(belief_set)
            except RuntimeError as e:
                self.logger.warning(
                    f"EProver unavailable ({e}), falling back to Tweety FOL reasoner"
                )
                return await self._fol_check_consistency_with_tweety_fallback(
                    belief_set
                )
        elif settings.solver == SolverChoice.MACE4:
            try:
                return await self._fol_check_consistency_with_mace4(belief_set)
            except SolverInputDefect:
                # #2504: an input the writer could not write, likewise.
                raise
            except RuntimeError as e:
                self.logger.warning(
                    f"Mace4 unavailable ({e}), falling back to Tweety FOL reasoner"
                )
                return await self._fol_check_consistency_with_tweety_fallback(
                    belief_set
                )
        else:
            return await self._fol_check_consistency_with_tweety(belief_set)

    async def _fol_check_consistency_with_tweety_fallback(self, belief_set):
        """Attempt Tweety FOL consistency check; returns solver_fallback=True on success."""
        try:
            result = await self._fol_check_consistency_with_tweety(belief_set)
            # result is (bool, str) — inject fallback flag
            is_consistent, msg = result
            return is_consistent, msg, True  # solver_fallback=True
        except Exception as tweety_err:
            self.logger.error(
                f"Tweety FOL fallback also failed: {tweety_err}",
                exc_info=True,
            )
            # Both solvers failed — propagate original issue
            raise RuntimeError(
                f"FOL consistency check failed: external solver absent and "
                f"Tweety fallback failed ({tweety_err})"
            ) from tweety_err

    async def _fol_check_consistency_with_prover9(self, belief_set):
        logger.debug(
            f"Checking FOL consistency for belief set of size {belief_set.size()} via external Prover9"
        )
        try:
            # #2482: one LADR clause per formula of the belief set. Its
            # ``toString()`` is set notation, which Prover9 rejects ("Set
            # parsing is not available"): this path had never decided.
            prover9_input = _prover9_input(belief_set)
            logger.debug(f"Prover9 input for consistency check:\n{prover9_input}")
            prover9_output = await asyncio.to_thread(run_prover9, prover9_input)
            # A proof of $F from the KB means the KB is inconsistent. A run
            # that ends on neither marker decided nothing: no verdict, rather
            # than "consistent" because no proof was printed.
            proved = _prover9_proved(prover9_output)
            if proved is None:
                msg = (
                    "Degraded (Prover9): no proof and no exhausted search; no verdict."
                )
                logger.warning(msg)
                return None, msg
            is_consistent = not proved
            msg = f"Prover9-based consistency check result: {is_consistent}"
            logger.info(msg)
            return is_consistent, msg
        except SolverInputDefect:
            # #2489: a refused input is the builder's defect; it keeps its type.
            raise
        except Exception as e:
            logger.error(
                f"Error during external FOL consistency check: {e}", exc_info=True
            )
            detailed_error = getattr(e, "stderr", str(e))
            raise RuntimeError(
                f"FOL consistency check failed. Details: {detailed_error}"
            ) from e

    async def _fol_check_consistency_with_tweety(self, belief_set):
        logger.debug(
            f"Performing FOL consistency check via Tweety for belief set of size {belief_set.size()}."
        )
        if not self._initializer_instance:
            raise ValueError(
                "TweetyInitializer instance is required for the 'tweety' solver path."
            )
        try:
            # A KB is inconsistent iff it entails the bottom symbol "-". Build the
            # contradiction with a LOCAL parser carrying the belief set's own
            # signature — NOT ``self.parse_fol_formula`` / ``self._fol_parser``,
            # which is only initialized when ``settings.solver == TWEETY`` and is
            # ``None`` otherwise (so under EPROVER/MACE4/PROVER9 init this method —
            # the external-solver FALLBACK and a comparison backend, FP-19 #1243 —
            # would spuriously fail). This mirrors the robust sync ``check_consistency``
            # and ``_fol_check_consistency_with_eprover`` paths.
            # #2494: the in-JVM reasoner's domain is read for what it decides.
            SimpleFolReasoner = self._initializer_instance.get_reasoner(
                "SimpleFolReasoner"
            )
            is_consistent, note = _in_jvm_consistency(SimpleFolReasoner, belief_set)
            msg = f"Tweety-based consistency check result: {is_consistent} ({note})"
            logger.info(msg)
            return is_consistent, msg

        except Exception as e:
            logger.error(
                f"Error during Tweety FOL consistency check: {e}", exc_info=True
            )
            raise NotImplementedError(
                f"The Tweety pathway for consistency checks failed: {e}"
            ) from e

    async def _fol_check_consistency_with_eprover(self, belief_set):
        """Checks FOL consistency using Tweety's EFOLReasoner (backed by EProver binary).

        #1196: the EProver binary path is read from the module-level
        ``EXTERNAL_TOOL_PATHS`` registry populated by ``jvm_setup._configure_external_tools``.
        The ``EFOLReasoner`` constructor takes that path as its single argument
        (Tweety 1.28+ API). Previously this method called ``EFOLReasoner()`` with
        no argument and relied on a global static path that was never set — so
        the EProver path always raised and fell back silently.
        """
        logger.debug(
            f"Performing FOL consistency check via EProver for belief set of size {belief_set.size()}."
        )
        eprover_path = _get_eprover_path()
        if eprover_path is None:
            raise RuntimeError(
                "EProver binary not detected (EXTERNAL_TOOL_PATHS['eprover'] unset); "
                "cannot run the 'eprover' solver path."
            )
        try:
            JString = jpype.JClass("java.lang.String")
            EFOLReasoner = jpype.JClass(
                "org.tweetyproject.logics.fol.reasoner.EFOLReasoner"
            )
            reasoner = EFOLReasoner(JString(eprover_path))

            # #1204 anti-théâtre guard: verify the Tweety->E delivery contract
            # actually carries the problem to the binary on this platform before
            # trusting any verdict. A broken contract silently returns
            # "consistent" on an inconsistent KB (fabrication, #1019).
            if not _eprover_delivery_is_reliable(reasoner, eprover_path):
                raise RuntimeError(
                    "EProver delivery contract broken on this platform "
                    "(sentinel {P(a),!P(a)} not reported inconsistent, #1204) — "
                    "refusing to serve a possibly-fabricated FOL verdict."
                )

            # Check consistency by querying the bottom/contradiction symbol "-"
            local_parser = jpype.JClass(
                "org.tweetyproject.logics.fol.parser.FolParser"
            )()
            local_parser.setSignature(belief_set.getMinimalSignature())
            contradiction = local_parser.parseFormula("-")
            inconsistent = reasoner.query(belief_set, contradiction)

            is_consistent = not bool(inconsistent)
            msg = f"EProver-based consistency check result: {is_consistent}"
            logger.info(msg)
            return is_consistent, msg
        except Exception as e:
            logger.error(
                f"Error during EProver FOL consistency check: {e}", exc_info=True
            )
            raise RuntimeError(f"EProver consistency check failed: {e}") from e

    async def _fol_check_consistency_with_mace4(self, belief_set):
        """Check FOL consistency using the Mace4 model-finder (FP-19 #1243).

        Mace4 is the SOUND CONSISTENT side of the multi-prover comparison: a
        finite model exhibits consistency. ``exhausted`` (no model up to the
        domain bound) is reported inconsistent, but the epistemic status is
        explicit (bounded model search, NOT a refutation proof). A timeout /
        crash surfaces as ``RuntimeError`` so the caller falls back honestly
        — never a fabricated verdict (#1019).

        The per-backend delivery sentinel runs first: if Mace4 cannot even find
        a model for a trivially-consistent KB, it is not reaching the binary and
        must not be trusted (raises → Tweety fallback).
        """
        logger.debug(
            f"Performing FOL consistency check via Mace4 for belief set of size "
            f"{belief_set.size()}."
        )
        if not MACE4_EXECUTABLE.is_file():
            raise RuntimeError(
                f"Mace4 binary not present at {MACE4_EXECUTABLE}; "
                "cannot run the 'mace4' solver path."
            )
        # Anti-théâtre delivery guard (#1019, #1204 generalized): verify Mace4
        # genuinely decides its SOUND direction before trusting any verdict.
        if not _mace4_delivery_is_reliable():
            raise RuntimeError(
                "Mace4 delivery contract broken (sentinel {ptest(a)} did not "
                "yield a finite model) — refusing to serve a possibly-fabricated "
                "FOL verdict."
            )
        try:
            ladr_input = _belief_set_to_ladr_assumptions(belief_set)
            logger.debug(f"Mace4 input for consistency check:\n{ladr_input}")
            mace4_output = await asyncio.to_thread(run_mace4, ladr_input)
            is_consistent, note = interpret_mace4_output(mace4_output)
            if is_consistent is None:
                # Degraded (resource limit, no verdict). Fail loud so the caller
                # falls back instead of fabricating — #1019.
                raise RuntimeError(f"Mace4 returned no verdict (degraded): {note}")
            msg = f"Mace4-based consistency check result: {is_consistent}. {note}"
            logger.info(msg)
            return is_consistent, msg
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(
                f"Error during Mace4 FOL consistency check: {e}", exc_info=True
            )
            raise RuntimeError(f"Mace4 consistency check failed: {e}") from e

    def fol_query(self, belief_set, query_formula_str: str):
        """
        Checks if a query is entailed by a belief base using the configured solver.

        When the external solver is unavailable (binary absent, RuntimeError),
        falls back to the in-JVM Tweety reasoner.  Returns a tuple
        ``(entailed: bool | None, solver_fallback: bool)`` so callers can track
        degradation. The in-JVM reasoner answers ``None`` when its domain does
        not decide the query (#2502).
        """
        logger.debug(f"Performing FOL query with solver: {settings.solver.value}")

        if settings.solver == SolverChoice.PROVER9:
            try:
                return (
                    self._fol_query_with_prover9(belief_set, query_formula_str),
                    False,
                )
            except SolverInputDefect:
                # #2489: Prover9 refused the input we built. The in-JVM
                # reasoner would answer, and the defect would stay invisible.
                raise
            except RuntimeError as e:
                logger.warning(
                    f"Prover9 unavailable ({e}), falling back to Tweety FOL query"
                )
                return self._fol_query_with_tweety(belief_set, query_formula_str), True
        elif settings.solver == SolverChoice.EPROVER:
            try:
                return (
                    self._fol_query_with_eprover(belief_set, query_formula_str),
                    False,
                )
            except RuntimeError as e:
                logger.warning(
                    f"EProver unavailable ({e}), falling back to Tweety FOL query"
                )
                return self._fol_query_with_tweety(belief_set, query_formula_str), True
        else:
            return self._fol_query_with_tweety(belief_set, query_formula_str), False

    def _parse_query(self, belief_set, query_str: str):
        """Parse a query against the belief set's declared signature.

        ``self._fol_parser`` is built only under the TWEETY solver, and it
        carries no KB's signature: ``fol_query`` raised under every solver
        (#2482). The declared signature, not the minimal one, because a
        constant declared only in a sort is absent from the minimal one (#2447).
        """
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        query_parser = FolParser()
        query_parser.setSignature(belief_set.getSignature())
        return self.parse_fol_formula(query_str, custom_parser=query_parser)

    def _fol_query_with_prover9(self, belief_set, query_formula_str: str) -> bool:
        """
        Ancienne logique d'interrogation via un processus externe Prover9.
        (Contenu de la méthode fol_query existante)
        """
        logger.debug(
            f"Performing FOL query via external Prover9. Query: '{query_formula_str}'"
        )
        try:
            # #2482: the goal is parsed against the KB's signature, then
            # translated like the KB's formulas. The Tweety string used to go
            # to Prover9 as is, after the belief set's set notation.
            goal = self._parse_query(belief_set, query_formula_str)
            prover9_input = _prover9_input(belief_set, goal)
            logger.debug(f"Prover9 input for query:\n{prover9_input}")
            prover9_output = run_prover9(prover9_input)

            entails = _prover9_proved(prover9_output)
            if entails is None:
                raise RuntimeError(
                    "Prover9 decided nothing: no proof and no exhausted search."
                )

            logger.info(f"FOL Query: KB entails '{query_formula_str}'? {entails}")
            return entails
        except SolverInputDefect:
            raise
        except Exception as e:
            logger.error(f"Error during external FOL query: {e}", exc_info=True)
            raise RuntimeError(
                f"FOL query failed. Details: {getattr(e, 'stderr', str(e))}"
            ) from e

    def _fol_query_with_tweety(
        self, belief_set, query_formula_str: str
    ) -> "bool | None":
        """
        Logique d'interrogation via Tweety/JPype. ``None`` when the in-JVM
        reasoner's domain does not decide the query (#2502).
        """
        logger.debug(f"Performing FOL query via Tweety. Query: '{query_formula_str}'")
        if not self._initializer_instance:
            raise ValueError(
                "TweetyInitializer instance is required for the 'tweety' solver path."
            )
        try:
            query_formula = self._parse_query(belief_set, query_formula_str)
            reasoner = self._initializer_instance.get_reasoner("SimpleFolReasoner")
            entails, note = _in_jvm_entailment(reasoner, belief_set, query_formula)
            logger.info(f"FOL query '{query_formula_str}' (in-JVM): {note}")
            return entails
        except Exception as e:
            logger.error(f"Error during Tweety FOL query: {e}", exc_info=True)
            raise

    def _fol_query_with_eprover(self, belief_set, query_formula_str: str) -> bool:
        """
        FOL query via Tweety's EFOLReasoner (backed by EProver binary).
        Uses the same Tweety parsing as the default path but delegates
        reasoning to the EProver theorem prover.
        """
        logger.debug(f"Performing FOL query via EProver. Query: '{query_formula_str}'")
        if not self._initializer_instance:
            raise ValueError(
                "TweetyInitializer instance is required for the 'eprover' solver path."
            )
        try:
            query_formula = self._parse_query(belief_set, query_formula_str)
            eprover_path = _get_eprover_path()
            if eprover_path is None:
                raise RuntimeError(
                    "EProver binary not detected (EXTERNAL_TOOL_PATHS['eprover'] unset)."
                )
            JString = jpype.JClass("java.lang.String")
            EFOLReasoner = jpype.JClass(
                "org.tweetyproject.logics.fol.reasoner.EFOLReasoner"
            )
            reasoner = EFOLReasoner(JString(eprover_path))
            entails = reasoner.query(belief_set, query_formula)
            logger.info(
                f"EProver query: KB entails '{query_formula_str}'? {bool(entails)}"
            )
            return bool(entails)
        except Exception as e:
            logger.error(f"Error during EProver FOL query: {e}", exc_info=True)
            raise

    def check_consistency(self, belief_set_input) -> tuple:
        """``(is_consistent, message)``: ``check_consistency_by`` without the
        name of the solver."""
        return self.check_consistency_by(belief_set_input)[:2]

    def check_consistency_by(self, belief_set_input, solver=None) -> tuple:
        """
        Check consistency of a FOL belief set, and say which solver decided.

        Accepts either a Tweety-syntax string (parsed via local FolParser)
        or a pre-built Java FolBeliefSet object.

        #1192 (anti-theater #1019): a parse-only or reasoner-less outcome is
        NOT a consistency verdict. Previously, on a reasoner exception or a
        missing initializer, this method returned ``(True, "Parsed
        successfully...")`` — a fabricated consistent verdict with no
        reasoning behind it. It now returns ``None`` (unknown/degraded) so
        downstream consumers cannot mistake "could not check" for "is
        consistent". Only a Tweety reasoner query determines consistency.

        ``solver`` overrides ``settings.solver`` for this call: the external
        FOL phase passes the solver its context asks for (#2482).

        Returns:
            Tuple[Optional[bool], str, Optional[str]]:
            ``(is_consistent, message, solver)``. ``is_consistent`` is
            ``True``/``False`` when a reasoner decided, or ``None`` when the
            check is degraded (reasoner unavailable or raised). ``solver`` is
            the reasoner the answer comes from: ``"eprover"``, ``"prover9"``,
            ``"mace4"`` or ``"tweety"`` (``SimpleFolReasoner``); ``None`` when
            no reasoner was reached. An empty belief set is trivially
            consistent (``True``, no solver).
        """
        choice = settings.solver if solver is None else SolverChoice(solver)
        try:
            # If it's a string, parse it into a Java belief set first
            if isinstance(belief_set_input, str):
                java_belief_set = self.create_belief_set_from_string(
                    belief_set_input.strip()
                )
            else:
                # Assume it's already a Java FolBeliefSet
                java_belief_set = belief_set_input

            if java_belief_set is None or java_belief_set.size() == 0:
                return True, "Empty belief set is trivially consistent.", None

            # MACE4 path (FP-19 #1243): the model-finder runs as a subprocess
            # (no in-JVM reasoner), so it is dispatched before the EProver/Tweety
            # reasoner selection. Same anti-théâtre discipline: degraded => None.
            if choice == SolverChoice.MACE4 and MACE4_EXECUTABLE.is_file():
                if not _mace4_delivery_is_reliable():
                    return (
                        None,
                        "Degraded: Mace4 delivery contract broken (sentinel "
                        "{ptest(a)} found no model, #1204); no consistency verdict.",
                        "mace4",
                    )
                try:
                    ladr_input = _belief_set_to_ladr_assumptions(java_belief_set)
                    mace4_output = run_mace4(ladr_input)
                    is_consistent, note = interpret_mace4_output(mace4_output)
                    if is_consistent is None:
                        return None, f"Degraded (Mace4): {note}", "mace4"
                    verdict = "consistent" if is_consistent else "inconsistent"
                    return (
                        is_consistent,
                        f"FOL consistency check (Mace4): {verdict}. {note}",
                        "mace4",
                    )
                except SolverInputDefect:
                    # #2504: the writer could not write our input; not an
                    # unavailable Mace4.
                    raise
                except Exception as e:
                    self.logger.warning(
                        f"Mace4 consistency check failed: {e}. Returning degraded "
                        "(None) — no fabricated verdict (#1019)."
                    )
                    return (
                        None,
                        f"Degraded: Mace4 unavailable ({e}); no verdict.",
                        "mace4",
                    )

            # #2482: this check, the one the FOL phase calls, ran
            # SimpleFolReasoner when PROVER9 was configured. Prover9 refutes: a
            # proof of $F from the KB means it is inconsistent. When it decides
            # nothing (binary absent, timeout, resource limit), the in-JVM
            # reasoner below decides, and the message says why.
            # #2489: an input Prover9 refuses is not one of those. We built
            # it, so the refusal raises with the binary's text; the fallback
            # used to answer instead, and a builder defect stayed invisible.
            fallback_note = ""
            if choice == SolverChoice.PROVER9:
                proved = None
                if not PROVER9_EXECUTABLE.is_file():
                    fallback_note = "Prover9 binary absent; "
                else:
                    try:
                        proved = _prover9_proved(
                            run_prover9(_prover9_input(java_belief_set))
                        )
                        fallback_note = "Prover9 decided nothing; "
                    except SolverInputDefect:
                        raise
                    except Exception as e:
                        first_line = (str(e).splitlines() or [""])[0]
                        fallback_note = f"Prover9 failed ({first_line}); "
                if proved is not None:
                    verdict = "inconsistent" if proved else "consistent"
                    return (
                        not proved,
                        f"FOL consistency check (Prover9): {verdict}",
                        "prover9",
                    )
                self.logger.warning(
                    f"{fallback_note}the in-JVM reasoner decides instead."
                )

            # Select the reasoner: the configured external solver (EProver) when
            # its binary is wired, otherwise Tweety's SimpleFolReasoner (#1196).
            # Previously this hardcoded SimpleFolReasoner regardless of
            # ``settings.solver`` — so a run configured for EProver silently
            # used the in-JVM reasoner (and OOM'd on large KBs), masking the
            # EProver integration as "active" when it never ran.
            eprover_path = _get_eprover_path()
            use_eprover = choice == SolverChoice.EPROVER and eprover_path is not None

            # Use the configured reasoner if available via initializer / registry
            if use_eprover or self._initializer_instance:
                try:
                    if use_eprover:
                        JString = jpype.JClass("java.lang.String")
                        EFOLReasoner = jpype.JClass(
                            "org.tweetyproject.logics.fol.reasoner.EFOLReasoner"
                        )
                        # use_eprover already implies eprover_path is not None
                        # (set above); narrow for the typed sentinel call below.
                        assert eprover_path is not None
                        reasoner = EFOLReasoner(JString(eprover_path))
                        solver_name = "EProver"
                        # #1204/#1232: this SYNC path is what
                        # ``TweetyBridge.check_consistency`` and the #1210 real-
                        # eprover test actually call. The #1232 sentinel guard
                        # was wired only into the ASYNC
                        # ``_fol_check_consistency_with_eprover`` — so on a
                        # platform with a broken Tweety->E delivery contract
                        # (Linux argc=0, firsthand #1204) this path STILL
                        # fabricated "consistent" on an inconsistent KB (#1019).
                        # Apply the SAME sentinel here: if the known-inconsistent
                        # {P(a),!P(a)} is not detected, eprover cannot be trusted
                        # on this platform — fall back to the in-JVM
                        # SimpleFolReasoner, which decides correctly, instead of
                        # serving a fabricated verdict.
                        if not _eprover_delivery_is_reliable(reasoner, eprover_path):
                            if self._initializer_instance is not None:
                                reasoner = self._initializer_instance.get_reasoner(
                                    "SimpleFolReasoner"
                                )
                                solver_name = "SimpleFolReasoner"
                            else:
                                return (
                                    None,
                                    "Degraded: EProver delivery contract broken "
                                    "(#1204) and no in-JVM reasoner available; "
                                    "no consistency verdict.",
                                    "eprover",
                                )
                    else:
                        reasoner = self._initializer_instance.get_reasoner(
                            "SimpleFolReasoner"
                        )
                        solver_name = "SimpleFolReasoner"
                    if solver_name == "SimpleFolReasoner":
                        # #2494: the in-JVM reasoner's domain is read for what
                        # it decides; an "inconsistent" it cannot make exact
                        # reads None.
                        is_consistent, note = _in_jvm_consistency(
                            reasoner, java_belief_set
                        )
                        msg = f"{fallback_note}FOL consistency check (SimpleFolReasoner): {note}"
                        return is_consistent, msg, "tweety"
                    # Check if KB entails a contradiction
                    # Use "-" (Tweety's built-in contradiction/bottom symbol)
                    # which doesn't require any predicates in the signature
                    local_parser = jpype.JClass(
                        "org.tweetyproject.logics.fol.parser.FolParser"
                    )()
                    local_parser.setSignature(java_belief_set.getMinimalSignature())
                    contradiction = local_parser.parseFormula("-")
                    inconsistent = reasoner.query(java_belief_set, contradiction)
                    is_consistent = not bool(inconsistent)
                    msg = f"{fallback_note}FOL consistency check ({solver_name}): {'consistent' if is_consistent else 'inconsistent'}"
                    label = "eprover" if solver_name == "EProver" else "tweety"
                    return is_consistent, msg, label
                except Exception as e:
                    # Fail-loud (anti-theater): parsing succeeded but the
                    # reasoner could not decide. Do NOT fabricate a consistent
                    # verdict — return degraded (None) so callers know the
                    # check did not run.
                    self.logger.warning(
                        f"Reasoner-based consistency check failed: {e}. "
                        "Returning degraded (None) — no consistency verdict."
                    )
                    return (
                        None,
                        "Degraded: reasoner unavailable; no consistency verdict (parse-only).",
                        None,
                    )
            else:
                # No initializer — cannot reason about consistency.
                # Fail-loud: degraded, not "consistent".
                return (
                    None,
                    "Degraded: no Tweety initializer; no consistency verdict.",
                    None,
                )

        except SolverInputDefect:
            # #2489: not a check that could not run, a defect in our input.
            raise
        except Exception as e:
            # #1290 (anti-theater #1019/#1278): an exception here means the
            # check could NOT run — most often a Tweety parse failure
            # ("Erreur de parsing Tweety") raised while building the belief set.
            # Returning ``False`` fabricated a *decided* "inconsistent" verdict
            # from a parse error: corpus_C's snapshot then carried
            # ``consistent=False`` and Acte II narrated a real "inconsistance"
            # that never happened. Per this method's own contract (docstring:
            # degraded => None), surface the honest unknown so downstream
            # consumers cannot mistake "could not check" for "is inconsistent".
            error_msg = str(e)
            self.logger.error(f"FOL consistency check failed: {error_msg}")
            return (
                None,
                f"Degraded: FOL consistency check error ({error_msg}); no verdict.",
                None,
            )

    async def compare_fol_backends(self, belief_set_input) -> dict:
        """Run ALL available FOL backends on the same belief set and compare.

        FP-19 #1243, mandate R468 ("tous les solvers handy … pour comparer les
        résultats"). Each backend (Tweety SimpleFolReasoner, EProver, Prover9,
        Mace4) is run INDEPENDENTLY on the same KB; verdicts are cross-validated.
        DISAGREEMENT is surfaced explicitly and NEVER silently reconciled — the
        comparison is the point (#1019).

        Soundness asymmetry (made explicit in the disagreement note):
        * EProver / Prover9 are sound on the **INCONSISTENT** side (refutation).
        * Mace4 is sound on the **CONSISTENT** side (a finite model is a witness);
          its "inconsistent" is only "no finite model ≤ domain bound", a bounded
          model search, NOT a refutation proof.
        * Tweety SimpleFolReasoner is the in-JVM baseline.

        Returns a JSON-serialisable dict::

            {
              "backends": {name: {"verdict": Optional[bool], "note": str,
                                  "elapsed_ms": float, "available": bool}},
              "decided":  {name: bool, …},     # only backends that returned a bool
              "agreement": Optional[bool],     # all-agree / disagree / <2 decided
              "disagreement": [str, …],        # explicit, never auto-reconciled
            }
        """
        # Build the Java belief set ONCE — every backend reasons over the same KB.
        if isinstance(belief_set_input, str):
            java_belief_set = self.create_belief_set_from_string(
                belief_set_input.strip()
            )
        else:
            java_belief_set = belief_set_input

        backends: "dict[str, dict]" = {}

        if java_belief_set is None or java_belief_set.size() == 0:
            trivial = {
                "verdict": True,
                "note": "Empty belief set is trivially consistent.",
                "elapsed_ms": 0.0,
                "available": True,
            }
            for name in ("tweety", "eprover", "prover9", "mace4"):
                backends[name] = dict(trivial)
            return {
                "backends": backends,
                "decided": {n: True for n in backends},
                "agreement": True,
                "disagreement": [],
            }

        async def _run(name, coro_factory) -> None:
            start = time.perf_counter()
            try:
                is_consistent, msg = await coro_factory()
                elapsed = (time.perf_counter() - start) * 1000.0
                backends[name] = {
                    "verdict": is_consistent,
                    "note": str(msg),
                    "elapsed_ms": round(elapsed, 1),
                    "available": True,
                }
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000.0
                backends[name] = {
                    "verdict": None,
                    "note": f"unavailable: {e}",
                    "elapsed_ms": round(elapsed, 1),
                    "available": False,
                }

        # Each per-backend method builds its own reasoner and applies its own
        # delivery sentinel, so they can be invoked directly regardless of the
        # globally-configured ``settings.solver``.
        await _run(
            "tweety", lambda: self._fol_check_consistency_with_tweety(java_belief_set)
        )
        await _run(
            "eprover", lambda: self._fol_check_consistency_with_eprover(java_belief_set)
        )
        await _run(
            "prover9", lambda: self._fol_check_consistency_with_prover9(java_belief_set)
        )
        await _run(
            "mace4", lambda: self._fol_check_consistency_with_mace4(java_belief_set)
        )

        decided = {
            name: b["verdict"]
            for name, b in backends.items()
            if isinstance(b["verdict"], bool)
        }
        verdict_values = set(decided.values())
        if len(decided) < 2:
            agreement: "bool | None" = None
        else:
            agreement = len(verdict_values) <= 1

        disagreement: "list[str]" = []
        if agreement is False:
            consistent_backends = sorted(n for n, v in decided.items() if v is True)
            inconsistent_backends = sorted(n for n, v in decided.items() if not v)
            disagreement.append(
                f"DISAGREEMENT (NOT reconciled): {consistent_backends} report "
                f"CONSISTENT, {inconsistent_backends} report INCONSISTENT. "
                "Soundness asymmetry — EProver/Prover9 are sound on the "
                "inconsistent (refutation) side; Mace4 is sound on the consistent "
                "(model-witness) side and its 'inconsistent' is only 'no finite "
                "model up to the domain bound', not a refutation proof. Inspect "
                "the per-backend notes before drawing a conclusion."
            )

        return {
            "backends": backends,
            "decided": decided,
            "agreement": agreement,
            "disagreement": disagreement,
        }

    def execute_fol_query(
        self, belief_set_input, query_str: str
    ) -> tuple[bool | None, str]:
        """
        Execute a FOL query (entailment check) against a belief set.

        Accepts either a Tweety-syntax string or a pre-built Java object
        for the belief set.

        Returns:
            Tuple[Optional[bool], str]: (entailed, message). ``True``/``False``
            only when the reasoner answered; ``None`` when no check ran (no
            initializer, no belief set, a parse or reasoner error), so that
            "could not check" never reads as "not entailed" (#2447).
        """
        if not self._initializer_instance:
            return None, "Degraded: no Tweety initializer; no query verdict."
        try:
            # Parse belief set if string
            if isinstance(belief_set_input, str):
                java_belief_set = self.create_belief_set_from_string(
                    belief_set_input.strip()
                )
            else:
                java_belief_set = belief_set_input

            if java_belief_set is None:
                return None, "Degraded: no belief set was built; no query verdict."

            query_formula = self._parse_query(java_belief_set, query_str)

            reasoner = self._initializer_instance.get_reasoner("SimpleFolReasoner")
            # #2502: the in-JVM domain is read for what it decides.
            entailed, note = _in_jvm_entailment(
                reasoner, java_belief_set, query_formula
            )
            return entailed, f"Query '{query_str}': {note}"

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"FOL query failed: {error_msg}")
            return None, f"Degraded: FOL query error ({error_msg}); no verdict."

    def validate_formula_with_signature(
        self, signature, formula_str: str
    ) -> tuple[bool, str]:
        """
        Validates a FOL formula string by creating a dedicated, temporary parser
        configured with the provided signature. This approach is thread-safe and
        avoids state-related issues with a shared parser.
        """
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")

        logger.debug(
            f"Validation de la formule '{formula_str}' avec une nouvelle instance de parser."
        )

        try:
            # 1. Create a new, isolated parser instance for this validation task.
            validation_parser = FolParser()

            # 2. Set the provided signature on this isolated parser.
            validation_parser.setSignature(signature)
            self.logger.debug(
                f"Signature (Hash: {signature.hashCode()}) appliquée au parser de validation."
            )

            # 3. Perform the parsing using the dedicated parser. If it succeeds, the formula is valid.
            self.parse_fol_formula(formula_str, custom_parser=validation_parser)
            self.logger.info(
                f"La formule FOL '{formula_str}' est valide avec la signature fournie."
            )
            return True, "Formule valide."

        except (jpype.JException, ValueError) as e:
            # If parse_fol_formula throws an exception, it means the formula is invalid
            # with respect to the given signature.
            error_message = f"Error parsing FOL formula '{formula_str}': {e}"
            self.logger.warning(error_message)
            return False, str(e)
