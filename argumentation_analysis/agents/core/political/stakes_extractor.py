"""Stakes & Stakeholders extraction specialist (Track TT #723).

Analyses discourse to identify:
- Stakes: what issues are at play (economic, political, ideological...)
- Stakeholders: which parties are engaged, with their stance
- Rhetorical register: the overall discourse strategy
- Discursive arena: the context/platform of the discourse

Uses LLM via OpenAI client with a structured JSON prompt.
Privacy: outputs pseudonymised references (Speaker_A, Group_X), never raw text.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("StakesExtractor")

EXTRACTION_PROMPT = (
    "You are a political-rhetorical analyst. Analyse the following discourse excerpt "
    "and extract FOUR elements in strict JSON format.\n\n"
    '1. "stakes": List of objects, each with:\n'
    '   - "stake_type": one of economic, political, ideological, security, identity, '
    "geopolitical, institutional, environmental, social, legal, technological\n"
    '   - "description": 10-20 word summary of what is at stake\n'
    '   - "evidence_indices": list of integers referencing argument positions '
    "(0-based) that support this stake identification\n\n"
    '2. "stakeholders": List of objects, each with:\n'
    '   - "name": pseudonymised (Speaker_A, Authority_X, Group_Y, Public_Z, etc.)\n'
    '   - "role": who they are in this discourse (speaker, opponent, audience, '
    "authority, institution, group)\n"
    '   - "stance": one of for, against, ambivalent, uncommitted\n'
    '   - "evidence_indices": list of integers referencing argument positions\n\n'
    '3. "rhetorical_register": ONE string from: mobilization, legitimation, '
    "delegitimization, polarization, anesthesia, technocratic, deliberative, protest\n\n"
    '4. "discursive_arena": ONE string describing the platform/context of the '
    'discourse (e.g. "parliamentary debate", "campaign rally", "academic conference", '
    '"media interview", "social media", "legal proceeding")\n\n'
    "Return ONLY valid JSON. No markdown fences. No commentary.\n\n"
    "Arguments identified (indexed 0..N):\n{arguments_block}\n\n"
    "Source metadata: speaker={speaker}, venue={venue}, topic={topic}, "
    "era={era}, language={language}.\n\n"
    "Discourse excerpt (first 3000 chars):\n{excerpt}"
)


class StakesExtractor:
    """Lightweight specialist for stakes & stakeholders extraction."""

    def extract(
        self,
        arguments: List[Dict[str, Any]],
        source_metadata: Dict[str, str],
        raw_text: str = "",
        llm_client: Optional[Any] = None,
        determinism_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract stakes, stakeholders, register, and arena from discourse.

        Args:
            arguments: List of argument dicts from shared state (with 'text' or
                       'description' keys).
            source_metadata: Speaker, venue, topic, era, language.
            raw_text: Full discourse text (truncated to 3000 chars for prompt).
            llm_client: OpenAI client with .chat.completions.create(). If None,
                        returns empty result.
            determinism_params: Optional temperature/seed for reproducibility.

        Returns:
            Dict matching UnifiedAnalysisState.stakes_and_stakeholders schema.
        """
        result: Dict[str, Any] = {
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        }

        if llm_client is None:
            logger.debug("No LLM client provided; returning empty stakes.")
            return result

        # Build arguments block for prompt
        args_lines = []
        for i, arg in enumerate(arguments[:30]):
            text = arg.get("text", arg.get("description", ""))
            if text:
                args_lines.append(f"[{i}] {text[:200]}")
        arguments_block = (
            "\n".join(args_lines) if args_lines else "(no arguments extracted)"
        )

        excerpt = (raw_text or "")[:3000]

        prompt = EXTRACTION_PROMPT.format(
            arguments_block=arguments_block,
            speaker=source_metadata.get("speaker", "unknown"),
            venue=source_metadata.get("venue", "unknown"),
            topic=source_metadata.get("topic", "unknown"),
            era=source_metadata.get(
                "era", source_metadata.get("date_or_year", "unknown")
            ),
            language=source_metadata.get("language", "unknown"),
            excerpt=excerpt,
        )

        try:
            params = determinism_params or {}
            response = llm_client.chat.completions.create(
                model=params.get("model", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=params.get("temperature", 0.3),
                **({} if "seed" not in params else {"seed": params["seed"]}),
            )
            content = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            parsed = json.loads(content)
            result["stakes"] = parsed.get("stakes", [])[:10]
            result["stakeholders"] = parsed.get("stakeholders", [])[:10]
            result["rhetorical_register"] = parsed.get("rhetorical_register", "")
            result["discursive_arena"] = parsed.get("discursive_arena", "")

            logger.info(
                f"Extracted {len(result['stakes'])} stakes, "
                f"{len(result['stakeholders'])} stakeholders, "
                f"register={result['rhetorical_register']}"
            )

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Stakes extraction parse error: {e}")
        except Exception as e:
            logger.warning(f"Stakes extraction LLM error: {e}")

        return result
