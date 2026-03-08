"""Tests for objective loading and validation."""

import tempfile
from pathlib import Path

import yaml
import pytest

from prae.objective import load_objective, Objective


def _write_objective(d, overrides=None):
    obj = {
        "name": "test",
        "repo_path": d,
        "mutable_paths": ["train.py"],
        "run_command": "python train.py",
        "budget_seconds": 60,
        "metric_name": "loss",
        "metric_goal": "minimize",
        "metric_regex": r"loss:\s*([\d.]+)",
        "max_iterations": 3,
    }
    if overrides:
        obj.update(overrides)
    path = Path(d) / "objective.yaml"
    with open(path, "w") as f:
        yaml.dump(obj, f)
    return str(path)


def test_load_basic():
    with tempfile.TemporaryDirectory() as d:
        path = _write_objective(d)
        obj = load_objective(path)
        assert obj.name == "test"
        assert obj.metric_goal == "minimize"
        assert obj.mutable_paths == ["train.py"]


def test_mutable_check():
    with tempfile.TemporaryDirectory() as d:
        path = _write_objective(d)
        obj = load_objective(path)
        assert obj.is_mutable("train.py") is True
        assert obj.is_mutable("model.py") is False


def test_invalid_goal():
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(ValueError, match="metric_goal"):
            path = _write_objective(d, {"metric_goal": "sideways"})
            load_objective(path)
