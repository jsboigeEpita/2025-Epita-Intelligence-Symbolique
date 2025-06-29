from typing import Callable, List, Dict, Any

class AnalysisLayer:
    """
    Base class for all analysis layers (jailbreak, bias, fallacy, output leak, etc.)
    """
    def __init__(self, name: str, system_prompt: str, llm_fn: Callable[[str], str], threshold: float = 0.5):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_fn = llm_fn
        self.threshold = threshold

    def analyze(self, prompt: str) -> Dict[str, Any]:
        """
        Returns a dict with score, pass/fail, and explanation.
        """
        input_text = f"{self.system_prompt}\nPrompt to analyze: {prompt}\nScore (0-1):"
        output = self.llm_fn(input_text)
        try:
            score = float(output.strip())
        except Exception:
            score = 1.0  # Default to malicious if parsing fails
        result = {
            "layer": self.name,
            "score": score,
            "passed": score < self.threshold,
            "explanation": f"Score={score} (threshold={self.threshold})"
        }
        return result