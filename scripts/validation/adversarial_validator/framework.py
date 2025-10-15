from typing import Callable, List, Dict, Any
from layer import AnalysisLayer
from validator import MultiLevelValidator


class SecureLLMFramework:
    """
    Main framework for secure LLM prompt processing.
    """

    def __init__(
        self,
        llm_fn: Callable[[str], str],
        analysis_layers: List[AnalysisLayer],
        output_analysis_layer: AnalysisLayer,
        input_validator: MultiLevelValidator = None,
        logger: Callable[[Dict[str, Any]], None] = None,
        main_llm_fn: Callable[[str], str] = None,  # NEW: for actual answer generation
    ):
        self.llm_fn = llm_fn
        self.analysis_layers = analysis_layers
        self.output_analysis_layer = output_analysis_layer
        self.validator = input_validator
        self.logger = logger
        self.main_llm_fn = main_llm_fn if main_llm_fn is not None else llm_fn

    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        report = {
            "input": prompt,
            "analysis": [],
            "output_analysis": None,
            "final_decision": None,
        }
        # Step 1: Multi-level validation
        if self.validator:
            validation = self.validator.validate(prompt)
            report["validation"] = validation
            if not validation["passed"]:
                report["final_decision"] = "rejected: input validation failed"
                if self.logger:
                    self.logger(report)
                return report
        # Step 3: Adversarial analysis layers
        for layer in self.analysis_layers:
            result = layer.analyze(prompt)
            report["analysis"].append(result)
            if not result["passed"]:
                report["final_decision"] = f"rejected: {layer.name} layer"
                if self.logger:
                    self.logger(report)
                return report
        # Step 4: Main LLM call (use main_llm_fn for actual answer)
        llm_output = self.main_llm_fn(prompt)
        report["llm_output"] = llm_output
        # Step 5: Output analysis (analyze the actual answer)
        output_result = self.output_analysis_layer.analyze(llm_output)
        report["output_analysis"] = output_result
        if not output_result["passed"]:
            report["final_decision"] = "rejected: output analysis"
            if self.logger:
                self.logger(report)
            return report
        report["final_decision"] = "accepted"
        if self.logger:
            self.logger(report)
        return report
