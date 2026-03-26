from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class StdioServerParameters:
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None