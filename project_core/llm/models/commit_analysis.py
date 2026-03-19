from pydantic import BaseModel, Field, ConfigDict
from typing import List

class CommitAnalysis(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    """
    Represents the qualitative analysis of a single Git commit.
    """
    detailed_summary: str = Field(
        description="A detailed, factual, and corrected summary of the commit's purpose and implementation, based on the diff and history."
    )
    technical_debt_signals: List[str] = Field(
        description="A list of identified technical debt signals, such as commented-out code, TODOs, or complex logic.",
        default_factory=list
    )
    quality_leaps: List[str] = Field(
        description="A list of identified quality leaps, such as significant refactoring, removal of dead code, or addition of tests.",
        default_factory=list
    )