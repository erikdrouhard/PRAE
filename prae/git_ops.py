"""Minimal git operations for rollback and lineage."""

import subprocess
from pathlib import Path
from typing import Optional


def _run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=check)


def current_ref(repo: Path) -> str:
    """Return the current HEAD short hash."""
    r = _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo)
    return r.stdout.strip()


def current_branch(repo: Path) -> str:
    """Return the current branch name."""
    r = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    return r.stdout.strip()


def is_clean(repo: Path) -> bool:
    """Check if the working tree is clean."""
    r = _run(["git", "status", "--porcelain"], cwd=repo)
    return r.stdout.strip() == ""


def checkout_branch(repo: Path, branch: str, create: bool = False) -> None:
    """Checkout a branch, optionally creating it."""
    cmd = ["git", "checkout"]
    if create:
        cmd.append("-b")
    cmd.append(branch)
    _run(cmd, cwd=repo)


def commit_file(repo: Path, filepath: str, message: str) -> str:
    """Stage and commit a single file. Returns the new commit hash.

    If there is nothing to commit (file unchanged), returns current ref without committing.
    """
    _run(["git", "add", filepath], cwd=repo)
    r = _run(["git", "-c", "commit.gpgsign=false", "commit", "-m", message], cwd=repo, check=False)
    if r.returncode != 0 and "nothing to commit" in r.stdout:
        pass  # No changes to commit
    elif r.returncode != 0:
        raise RuntimeError(f"git commit failed: {r.stderr}")
    return current_ref(repo)


def revert_to(repo: Path, ref: str) -> None:
    """Hard reset to a given ref. Use for clean rollback."""
    _run(["git", "reset", "--hard", ref], cwd=repo)


def create_branch(repo: Path, branch_name: str) -> None:
    """Create a branch at current HEAD without switching to it."""
    _run(["git", "branch", branch_name], cwd=repo, check=False)


def diff_stat(repo: Path) -> str:
    """Return a short diff stat of staged/unstaged changes."""
    r = _run(["git", "diff", "--stat"], cwd=repo, check=False)
    return r.stdout.strip()


def changed_files(repo: Path) -> list[str]:
    """Return list of changed files (staged + unstaged)."""
    r = _run(["git", "diff", "--name-only", "HEAD"], cwd=repo, check=False)
    files = [f for f in r.stdout.strip().split("\n") if f]
    # Also check untracked
    r2 = _run(["git", "ls-files", "--others", "--exclude-standard"], cwd=repo, check=False)
    untracked = [f for f in r2.stdout.strip().split("\n") if f]
    return files + untracked


def stash_save(repo: Path) -> None:
    """Stash current changes."""
    _run(["git", "stash", "push", "-m", "prae-stash"], cwd=repo, check=False)


def stash_pop(repo: Path) -> None:
    """Pop stashed changes."""
    _run(["git", "stash", "pop"], cwd=repo, check=False)


def ensure_branch(repo: Path, branch: str) -> None:
    """Ensure we are on the given branch, creating it if necessary."""
    cur = current_branch(repo)
    if cur != branch:
        # Try to checkout, create if doesn't exist
        r = _run(["git", "checkout", branch], cwd=repo, check=False)
        if r.returncode != 0:
            checkout_branch(repo, branch, create=True)
