import jpype
import logging
import asyncio

# La configuration du logging (appel à setup_logging()) est supposée être faite globalement.
from argumentation_analysis.core.utils.logging_utils import setup_logging
from .tweety_initializer import TweetyInitializer
from argumentation_analysis.core.prover9_runner import run_prover9
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
            except RuntimeError as e:
                self.logger.warning(
                    f"Prover9 unavailable ({e}), falling back to Tweety FOL reasoner"
                )
                return await self._fol_check_consistency_with_tweety_fallback(belief_set)
        elif settings.solver == SolverChoice.EPROVER:
            try:
                return await self._fol_check_consistency_with_eprover(belief_set)
            except RuntimeError as e:
                self.logger.warning(
                    f"EProver unavailable ({e}), falling back to Tweety FOL reasoner"
                )
                return await self._fol_check_consistency_with_tweety_fallback(belief_set)
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
            formulas_str = belief_set.toString().replace(";", ".\n")
            # FP-8: correct Prover9 syntax — goals must be wrapped in
            # ``formulas(goals).`` (the bare ``goals.`` list header is rejected
            # by Prover9 2009-11A with "Fatal error: Unrecognized command"). A
            # consistency check asks whether the KB entails falsehood ($F): a
            # proof of $F = inconsistent.
            prover9_input = f"formulas(assumptions).\n{formulas_str}\nend_of_list.\n\nformulas(goals).\n$F.\nend_of_list."
            logger.debug(f"Prover9 input for consistency check:\n{prover9_input}")
            prover9_output = await asyncio.to_thread(run_prover9, prover9_input)
            # FP-8: the real proof-found marker emitted by Prover9 2009-11A is
            # "THEOREM PROVED" (the previous code looked for "END OF PROOF" in
            # the wrong case — it never matched, so an inconsistent KB was
            # reported as consistent = théâtre). Proof found (KB entails $F) ⇒
            # inconsistent.
            is_consistent = "THEOREM PROVED" not in prover9_output
            msg = f"Consistency check result: {is_consistent}"
            logger.info(msg)
            return is_consistent, msg
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
            # This method requires a reasoner that can check for consistency.
            # SimpleFolReasoner does not have a direct `isConsistent` method,
            # but we can infer it. A knowledge base is inconsistent if it entails a contradiction (e.g., "$false").
            FolFormula = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolFormula")
            # Tweety's representation of contradiction might be different, let's use a common one.
            # A more robust solution would be to use a specific Tweety constant for falsehood.
            contradiction = self.parse_fol_formula("forall X (X = X & not(X=X))")

            SimpleFolReasoner = self._initializer_instance.get_reasoner(
                "SimpleFolReasoner"
            )
            inconsistent = SimpleFolReasoner.query(belief_set, contradiction)

            is_consistent = not bool(inconsistent)
            msg = f"Tweety-based consistency check result: {is_consistent}"
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

    def fol_query(self, belief_set, query_formula_str: str):
        """
        Checks if a query is entailed by a belief base using the configured solver.

        When the external solver is unavailable (binary absent, RuntimeError),
        falls back to the in-JVM Tweety reasoner.  Returns a tuple
        ``(entailed: bool, solver_fallback: bool)`` so callers can track
        degradation.
        """
        logger.debug(f"Performing FOL query with solver: {settings.solver.value}")

        if settings.solver == SolverChoice.PROVER9:
            try:
                return self._fol_query_with_prover9(belief_set, query_formula_str), False
            except RuntimeError as e:
                logger.warning(
                    f"Prover9 unavailable ({e}), falling back to Tweety FOL query"
                )
                return self._fol_query_with_tweety(belief_set, query_formula_str), True
        elif settings.solver == SolverChoice.EPROVER:
            try:
                return self._fol_query_with_eprover(belief_set, query_formula_str), False
            except RuntimeError as e:
                logger.warning(
                    f"EProver unavailable ({e}), falling back to Tweety FOL query"
                )
                return self._fol_query_with_tweety(belief_set, query_formula_str), True
        else:
            return self._fol_query_with_tweety(belief_set, query_formula_str), False

    def _fol_query_with_prover9(self, belief_set, query_formula_str: str) -> bool:
        """
        Ancienne logique d'interrogation via un processus externe Prover9.
        (Contenu de la méthode fol_query existante)
        """
        logger.debug(
            f"Performing FOL query via external Prover9. Query: '{query_formula_str}'"
        )
        try:
            # Convert belief set and query to Prover9 input format
            formulas_str = belief_set.toString().replace(";", ".\n")
            prover9_goal = query_formula_str.rstrip(".")
            # FP-8: correct Prover9 syntax — ``formulas(goals).`` not bare
            # ``goals.`` (see consistency check above). Validated empirically
            # against Prover9 2009-11A.
            prover9_input = f"formulas(assumptions).\n{formulas_str}\nend_of_list.\n\nformulas(goals).\n{prover9_goal}.\nend_of_list."

            logger.debug(f"Prover9 input for query:\n{prover9_input}")

            # Run Prover9 externally
            prover9_output = run_prover9(prover9_input)

            # FP-8: the real proof-found marker is "THEOREM PROVED" (Prover9
            # 2009-11A). "END OF PROOF" never matched (wrong case) so every
            # entailment query returned False even when the goal was proven.
            entails = "THEOREM PROVED" in prover9_output

            logger.info(f"FOL Query: KB entails '{query_formula_str}'? {entails}")
            return entails
        except Exception as e:
            logger.error(f"Error during external FOL query: {e}", exc_info=True)
            raise RuntimeError(
                f"FOL query failed. Details: {getattr(e, 'stderr', str(e))}"
            ) from e

    def _fol_query_with_tweety(self, belief_set, query_formula_str: str) -> bool:
        """
        Logique d'interrogation via Tweety/JPype.
        """
        logger.debug(f"Performing FOL query via Tweety. Query: '{query_formula_str}'")
        if not self._initializer_instance:
            raise ValueError(
                "TweetyInitializer instance is required for the 'tweety' solver path."
            )
        try:
            query_formula = self.parse_fol_formula(query_formula_str)
            reasoner = self._initializer_instance.get_reasoner("SimpleFolReasoner")
            entails = reasoner.query(belief_set, query_formula)
            return bool(entails)
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
            query_formula = self.parse_fol_formula(query_formula_str)
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
        """
        Check consistency of a FOL belief set.

        Accepts either a Tweety-syntax string (parsed via local FolParser)
        or a pre-built Java FolBeliefSet object.

        #1192 (anti-theater #1019): a parse-only or reasoner-less outcome is
        NOT a consistency verdict. Previously, on a reasoner exception or a
        missing initializer, this method returned ``(True, "Parsed
        successfully...")`` — a fabricated consistent verdict with no
        reasoning behind it. It now returns ``None`` (unknown/degraded) so
        downstream consumers cannot mistake "could not check" for "is
        consistent". Only a Tweety reasoner query determines consistency.

        Returns:
            Tuple[Optional[bool], str]: ``(is_consistent, message)`` where
            ``is_consistent`` is ``True``/``False`` when the reasoner decided,
            or ``None`` when the check is degraded (reasoner unavailable or
            raised). An empty belief set is trivially consistent (``True``).
        """
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
                return True, "Empty belief set is trivially consistent."

            # Select the reasoner: the configured external solver (EProver) when
            # its binary is wired, otherwise Tweety's SimpleFolReasoner (#1196).
            # Previously this hardcoded SimpleFolReasoner regardless of
            # ``settings.solver`` — so a run configured for EProver silently
            # used the in-JVM reasoner (and OOM'd on large KBs), masking the
            # EProver integration as "active" when it never ran.
            eprover_path = _get_eprover_path()
            use_eprover = (
                settings.solver == SolverChoice.EPROVER and eprover_path is not None
            )

            # Use the configured reasoner if available via initializer / registry
            if use_eprover or self._initializer_instance:
                try:
                    if use_eprover:
                        JString = jpype.JClass("java.lang.String")
                        EFOLReasoner = jpype.JClass(
                            "org.tweetyproject.logics.fol.reasoner.EFOLReasoner"
                        )
                        reasoner = EFOLReasoner(JString(eprover_path))
                        solver_name = "EProver"
                    else:
                        reasoner = self._initializer_instance.get_reasoner(
                            "SimpleFolReasoner"
                        )
                        solver_name = "SimpleFolReasoner"
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
                    msg = f"FOL consistency check ({solver_name}): {'consistent' if is_consistent else 'inconsistent'}"
                    return is_consistent, msg
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
                    )
            else:
                # No initializer — cannot reason about consistency.
                # Fail-loud: degraded, not "consistent".
                return None, "Degraded: no Tweety initializer; no consistency verdict."

        except (ValueError, Exception) as e:
            error_msg = str(e)
            self.logger.error(f"FOL consistency check failed: {error_msg}")
            return False, f"FOL consistency check error: {error_msg}"

    def execute_fol_query(self, belief_set_input, query_str: str) -> tuple:
        """
        Execute a FOL query (entailment check) against a belief set.

        Accepts either a Tweety-syntax string or a pre-built Java object
        for the belief set.

        Returns:
            Tuple[bool, str]: (entailed, message)
        """
        try:
            # Parse belief set if string
            if isinstance(belief_set_input, str):
                java_belief_set = self.create_belief_set_from_string(
                    belief_set_input.strip()
                )
            else:
                java_belief_set = belief_set_input

            if java_belief_set is None:
                return False, "Failed to create belief set."

            # Parse query formula with the belief set's signature
            FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
            query_parser = FolParser()
            query_parser.setSignature(java_belief_set.getMinimalSignature())
            query_formula = query_parser.parseFormula(query_str)

            # Use reasoner if available
            if self._initializer_instance:
                reasoner = self._initializer_instance.get_reasoner("SimpleFolReasoner")
                entailed = bool(reasoner.query(java_belief_set, query_formula))
                msg = (
                    f"Query '{query_str}': {'entailed' if entailed else 'not entailed'}"
                )
                return entailed, msg
            else:
                return False, "No Tweety initializer available for query."

        except (ValueError, Exception) as e:
            error_msg = str(e)
            self.logger.error(f"FOL query failed: {error_msg}")
            return False, f"FOL query error: {error_msg}"

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
