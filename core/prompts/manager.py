import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List


class PromptTemplate:
    """Represents a loaded prompt template directory."""

    def __init__(
        self,
        name: str,
        path: Path,
        config: Dict[str, Any],
        parameters: Dict[str, Any],
        prompt_text: str,
    ):
        self.name = name
        self.path = path
        self.config = config
        self.parameters = parameters
        self.prompt_text = prompt_text

    def __repr__(self):
        return f"PromptTemplate(name='{self.name}')"


class PromptRenderer:
    """Renders a prompt template with the given context."""

    def render(self, template: PromptTemplate, context: Dict[str, Any]) -> str:
        processed_text = self._process_optimization_blocks(template, context)
        final_text = self._render_simple_variables(processed_text, context)
        return final_text.strip()

    def _render_simple_variables(self, text: str, context: Dict[str, Any]) -> str:
        def replace(match):
            key_path = match.group(1).strip().split(".")
            value = context
            try:
                for key in key_path:
                    if isinstance(value, dict):
                        value = value.get(key)
                    else:
                        value = getattr(value, key, None)
                    if value is None:
                        return ""
                return str(value) if value is not None else ""
            except (KeyError, TypeError, AttributeError):
                return ""

        return re.sub(r"\{\{\s*([\w\.]+)\s*\}\}", replace, text)

    def _process_optimization_blocks(
        self, template: PromptTemplate, context: Dict[str, Any]
    ) -> str:
        # This regex now consumes surrounding whitespace to avoid blank lines
        pattern = re.compile(
            r"\s*\{\#optimize_axis\s+(?P<params>.*?)\}(?P<body>.*?)\{\/optimize_axis\}\s*",
            re.DOTALL,
        )
        template_axes = {
            axis["name"]: axis
            for axis in template.parameters.get("optimization_axes", [])
        }

        def replace_block(match):
            params = dict(
                re.findall(r'(\w+)=["\']?([^"\']+)["\']?', match.group("params"))
            )
            body = match.group("body")
            axis_name = params.get("name")
            if not axis_name or axis_name not in template_axes:
                return ""

            axis_config = template_axes[axis_name]
            axis_value = context.get("optimization_params", {}).get(
                axis_name, axis_config.get("default")
            )

            should_render = False
            if "value" in params:
                if str(axis_value) == params["value"]:
                    should_render = True
            elif "min" in params:
                if axis_value is not None and int(axis_value or 0) >= int(
                    params["min"]
                ):
                    should_render = True

            return (
                self._process_loops(body, context, axis_value, axis_name)
                if should_render
                else ""
            )

        return pattern.sub(replace_block, template.prompt_text)

    def _process_loops(
        self, body: str, context: Dict[str, Any], axis_value: Any, axis_name: str
    ) -> str:
        # This regex now supports dotted paths for variables
        loop_pattern = re.compile(
            r'\{\#loop\s+variable=["\']([\w\.]+)["\']\s*(?P<params>.*?)\}(?P<loop_body>.*?)\{\/loop\}',
            re.DOTALL,
        )

        def replace_loop(match):
            var_path = match.group(1).split(".")
            loop_params = dict(
                re.findall(r'(\w+)=["\']?([^"\']+)["\']?', match.group("params"))
            )
            loop_body = match.group("loop_body")

            items = context
            try:
                for key in var_path:
                    items = items[key]
            except (KeyError, TypeError):
                items = []

            if not isinstance(items, list):
                return ""

            count = len(items)
            if "count_from" in loop_params and loop_params["count_from"] == axis_name:
                count = int(axis_value or 0)
            elif "count" in loop_params:
                count = int(loop_params["count"])

            result = []
            for i, item_data in enumerate(items[:count]):
                loop_context = {**context, "item": item_data, "index": i + 1}
                result.append(self._render_simple_variables(loop_body, loop_context))
            return "".join(result)

        return loop_pattern.sub(replace_loop, body)


class PromptManager:
    def __init__(self, templates_directory: str = "core/prompt_templates"):
        self.templates_path = Path(templates_directory)
        self.templates: Dict[str, PromptTemplate] = {}
        self.renderer = PromptRenderer()
        self.discover_templates()

    def discover_templates(self):
        if not self.templates_path.is_dir():
            return
        for template_dir in self.templates_path.iterdir():
            if template_dir.is_dir():
                try:
                    self.templates[template_dir.name] = self._load_template(
                        template_dir
                    )
                except FileNotFoundError as e:
                    print(f"Skipping incomplete template: {e}")

    def _load_template(self, template_path: Path) -> PromptTemplate:
        files = {p.name: p for p in template_path.iterdir()}
        required = ["config.json", "parameters.json", "skprompt.txt"]
        if not all(r in files for r in required):
            raise FileNotFoundError(f"Missing files in {template_path.name}")
        return PromptTemplate(
            name=template_path.name,
            path=template_path,
            config=json.loads(files["config.json"].read_text()),
            parameters=json.loads(files["parameters.json"].read_text()),
            prompt_text=files["skprompt.txt"].read_text(),
        )

    def render_prompt(self, template_name: str, context: Dict[str, Any]) -> str:
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found.")
        return self.renderer.render(self.templates[template_name], context)


if __name__ == "__main__":
    manager = PromptManager()
    print("--- Template Discovery ---")
    if "sample_analysis_v1" in manager.templates:
        print("Successfully discovered 'sample_analysis_v1'")

        print("\n" + "=" * 40 + "\n")
        test_context_1 = {
            "input": "This is a test input text.",
            "optimization_params": {"rag_depth": "summary", "example_count": 0},
            "rag_results": {"summary": "This is the summary of the RAG document."},
        }
        rendered_text_1 = manager.render_prompt("sample_analysis_v1", test_context_1)
        print("--- Render Test 1 (rag_depth=summary, example_count=0) ---")
        print(rendered_text_1)

        print("\n" + "=" * 40 + "\n")
        test_context_2 = {
            "input": "This is another test input.",
            "optimization_params": {"rag_depth": "top_3_chunks", "example_count": 2},
            "rag_results": {
                "chunks": [
                    {"chunk_text": "First relevant chunk."},
                    {"chunk_text": "Second relevant chunk."},
                ]
            },
            "examples": [
                {
                    "text": "Cats are better than dogs.",
                    "fallacy_type": "Hasty Generalization",
                },
                {
                    "text": "You are either with us, or against us.",
                    "fallacy_type": "False Dichotomy",
                },
            ],
        }
        rendered_text_2 = manager.render_prompt("sample_analysis_v1", test_context_2)
        print("--- Render Test 2 (rag_depth=top_3_chunks, example_count=2) ---")
        print(rendered_text_2)
        print("=" * 40)
    else:
        print("Could not find 'sample_analysis_v1'. Check paths.")
