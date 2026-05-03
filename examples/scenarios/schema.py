"""Pydantic schema for scenario manifest validation."""
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ScenarioSpec(BaseModel):
    """A single scenario specification."""
    id: str = Field(pattern=r"^scenario_\w+$")
    file: str
    title: str
    theme: str
    language: str = "fr"
    expected_capabilities: List[str] = Field(min_length=1)
    acceptance_min_args: int = Field(ge=1)
    acceptance_min_fallacies: int = Field(ge=0)


class ScenarioManifest(BaseModel):
    """Root manifest for scenario fixtures."""
    scenarios: List[ScenarioSpec] = Field(min_length=1)

    @field_validator("scenarios")
    @classmethod
    def unique_ids(cls, v: List[ScenarioSpec]) -> List[ScenarioSpec]:
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate scenario IDs")
        return v


def load_manifest(path: Path) -> ScenarioManifest:
    """Load and validate a scenario manifest from YAML."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ScenarioManifest.model_validate(raw)
