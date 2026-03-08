"""Load and validate objective.yaml — the human control point."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Objective:
    name: str
    repo_path: str
    mutable_paths: list[str]
    baseline_ref: str
    run_command: str
    budget_seconds: int
    metric_name: str
    metric_goal: str  # "minimize" or "maximize"
    metric_regex: str
    max_iterations: int
    provider: str = "openai"
    model: str = "gpt-4o"
    api_base: Optional[str] = None
    improvement_threshold: Optional[float] = None
    notes: str = ""
    instructions: str = ""

    def __post_init__(self):
        if self.metric_goal not in ("minimize", "maximize"):
            raise ValueError(f"metric_goal must be 'minimize' or 'maximize', got '{self.metric_goal}'")
        if not self.mutable_paths:
            raise ValueError("mutable_paths must not be empty")
        if self.budget_seconds <= 0:
            raise ValueError("budget_seconds must be positive")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")

    @property
    def repo(self) -> Path:
        return Path(self.repo_path).resolve()

    def is_mutable(self, path: str) -> bool:
        """Check whether a file path is in the mutable surface."""
        rel = str(Path(path))
        return any(rel == m or rel.endswith("/" + m) for m in self.mutable_paths)


def load_objective(path: str | Path) -> Objective:
    """Load an objective from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    return Objective(
        name=data["name"],
        repo_path=data["repo_path"],
        mutable_paths=data.get("mutable_paths", ["train.py"]),
        baseline_ref=data.get("baseline_ref", "main"),
        run_command=data["run_command"],
        budget_seconds=data.get("budget_seconds", 300),
        metric_name=data["metric_name"],
        metric_goal=data.get("metric_goal", "minimize"),
        metric_regex=data["metric_regex"],
        max_iterations=data.get("max_iterations", 10),
        provider=data.get("provider", "openai"),
        model=data.get("model", "gpt-4o"),
        api_base=data.get("api_base"),
        improvement_threshold=data.get("improvement_threshold"),
        notes=data.get("notes", ""),
        instructions=data.get("instructions", ""),
    )
