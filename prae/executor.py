"""Execute the target run_command under a time budget."""

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RunResult:
    stdout: str
    stderr: str
    returncode: int
    elapsed_seconds: float
    timed_out: bool


def run_target(run_command: str, cwd: Path, budget_seconds: int) -> RunResult:
    """Run the target command with a wall-clock budget."""
    start = time.time()
    try:
        proc = subprocess.run(
            run_command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=budget_seconds,
        )
        elapsed = time.time() - start
        return RunResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
            elapsed_seconds=elapsed,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start
        return RunResult(
            stdout=e.stdout or "" if isinstance(e.stdout, str) else (e.stdout.decode() if e.stdout else ""),
            stderr=e.stderr or "" if isinstance(e.stderr, str) else (e.stderr.decode() if e.stderr else ""),
            returncode=-1,
            elapsed_seconds=elapsed,
            timed_out=True,
        )


def parse_metric(output: str, metric_regex: str) -> Optional[float]:
    """Extract metric value from command output using the objective's regex.

    The regex must contain exactly one capture group for the numeric value.
    """
    match = re.search(metric_regex, output)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            return None
    return None
