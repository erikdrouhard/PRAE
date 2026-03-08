"""Smoke test: run a full dry-run loop in both modes."""

import tempfile
import subprocess
import shutil
from pathlib import Path

import yaml

from prae.loop import run
from prae.ledger import read_entries


def _setup_target_repo(d):
    """Create a minimal target repo with a train.py that emits a metric."""
    subprocess.run(["git", "init"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=d, capture_output=True, check=True)

    train = Path(d) / "train.py"
    train.write_text(
        'import random\n'
        'random.seed(42)\n'
        'loss = random.uniform(0.3, 0.7)\n'
        'print(f"final_loss: {loss:.6f}")\n'
    )
    subprocess.run(["git", "add", "train.py"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=d, capture_output=True, check=True)


def _write_objective(d, repo_path):
    obj = {
        "name": "dry-run-test",
        "repo_path": repo_path,
        "mutable_paths": ["train.py"],
        "run_command": "python train.py",
        "budget_seconds": 30,
        "metric_name": "loss",
        "metric_goal": "minimize",
        "metric_regex": r"final_loss:\s*([\d.]+)",
        "max_iterations": 2,
    }
    path = Path(d) / "objective.yaml"
    with open(path, "w") as f:
        yaml.dump(obj, f)
    return str(path)


def test_dry_run_baseline():
    with tempfile.TemporaryDirectory() as d:
        repo_dir = str(Path(d) / "repo")
        Path(repo_dir).mkdir()
        _setup_target_repo(repo_dir)

        obj_path = _write_objective(d, repo_dir)
        ledger_path = str(Path(d) / "ledger.jsonl")

        run(obj_path, mode="baseline", ledger_path=ledger_path, dry_run=True)

        entries = read_entries(ledger_path)
        assert len(entries) == 2
        assert all(e.mode == "baseline" for e in entries)


def test_dry_run_prae():
    with tempfile.TemporaryDirectory() as d:
        repo_dir = str(Path(d) / "repo")
        Path(repo_dir).mkdir()
        _setup_target_repo(repo_dir)

        obj_path = _write_objective(d, repo_dir)
        ledger_path = str(Path(d) / "ledger.jsonl")

        run(obj_path, mode="prae", ledger_path=ledger_path, dry_run=True)

        entries = read_entries(ledger_path)
        assert len(entries) == 2
        assert all(e.mode == "prae" for e in entries)
        # PRAE entries should have rebuttal and audit summaries
        for e in entries:
            assert e.rebuttal_summary or e.notes  # either has rebuttal or was rejected early
