"""Tests for git operations — revert behavior."""

import tempfile
import subprocess
from pathlib import Path

from prae.git_ops import current_ref, commit_file, revert_to, create_branch


def _init_repo(d):
    """Initialize a git repo with one commit."""
    subprocess.run(["git", "init"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=d, capture_output=True, check=True)
    # Initial commit
    (Path(d) / "train.py").write_text("# initial\n")
    subprocess.run(["git", "add", "train.py"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=d, capture_output=True, check=True)


def test_commit_and_revert():
    with tempfile.TemporaryDirectory() as d:
        _init_repo(d)
        repo = Path(d)

        initial_ref = current_ref(repo)

        # Modify and commit
        (repo / "train.py").write_text("# modified\n")
        new_ref = commit_file(repo, "train.py", "test change")
        assert new_ref != initial_ref
        assert (repo / "train.py").read_text() == "# modified\n"

        # Revert
        revert_to(repo, initial_ref)
        assert (repo / "train.py").read_text() == "# initial\n"


def test_create_branch():
    with tempfile.TemporaryDirectory() as d:
        _init_repo(d)
        repo = Path(d)

        create_branch(repo, "prae/test-branch")
        r = subprocess.run(["git", "branch", "--list", "prae/test-branch"],
                          cwd=d, capture_output=True, text=True)
        assert "prae/test-branch" in r.stdout
