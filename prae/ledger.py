"""Line-oriented JSONL ledger for recording each PRAE cycle."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class LedgerEntry:
    iteration: int
    mode: str  # "baseline" or "prae"
    timestamp: str
    baseline_ref: str
    proposal_summary: str = ""
    rebuttal_summary: str = ""
    pre_audit_summary: str = ""
    patch_summary: str = ""
    run_command: str = ""
    budget_seconds: int = 0
    execution_status: str = ""  # "success", "timeout", "error"
    parsed_metric: Optional[float] = None
    post_audit_summary: str = ""
    verdict: str = ""  # keep/revert/revise/branch/escalate (prae) or keep/discard (baseline)
    baseline_advanced: bool = False
    branch_name: str = ""
    notes: str = ""
    errors: str = ""


def append_entry(ledger_path: str | Path, entry: LedgerEntry) -> None:
    """Append one entry to the JSONL ledger."""
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")


def read_entries(ledger_path: str | Path) -> list[LedgerEntry]:
    """Read all entries from a JSONL ledger."""
    path = Path(ledger_path)
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(LedgerEntry(**json.loads(line)))
    return entries
