"""Load and validate config.yaml."""
from __future__ import annotations
import dataclasses, pathlib, yaml
from typing import Any

_DEFAULT = pathlib.Path(__file__).parent.parent.parent / "config.yaml"

@dataclasses.dataclass
class Config:
    roles: list[str]
    keywords_priority: list[str]
    locations: list[str]
    salary_min_usd: int
    score_threshold: int
    max_results: int
    bio: str
    sources: dict[str, Any]

    @classmethod
    def load(cls, path: pathlib.Path = _DEFAULT) -> "Config":
        data = yaml.safe_load(path.read_text())
        return cls(**data)
