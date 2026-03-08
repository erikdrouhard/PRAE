"""Tests for mutable surface enforcement."""

import tempfile
import subprocess
from pathlib import Path

from prae.objective import Objective


def test_is_mutable_allows_train():
    obj = Objective(
        name="test", repo_path="/tmp", mutable_paths=["train.py"],
        baseline_ref="main", run_command="echo ok", budget_seconds=10,
        metric_name="loss", metric_goal="minimize",
        metric_regex=r"loss:\s*([\d.]+)", max_iterations=3,
    )
    assert obj.is_mutable("train.py") is True
    assert obj.is_mutable("/some/path/train.py") is True


def test_is_mutable_blocks_other():
    obj = Objective(
        name="test", repo_path="/tmp", mutable_paths=["train.py"],
        baseline_ref="main", run_command="echo ok", budget_seconds=10,
        metric_name="loss", metric_goal="minimize",
        metric_regex=r"loss:\s*([\d.]+)", max_iterations=3,
    )
    assert obj.is_mutable("model.py") is False
    assert obj.is_mutable("config.yaml") is False
    assert obj.is_mutable("prae/loop.py") is False
