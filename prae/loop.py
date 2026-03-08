"""PRAE runtime loop.

Two modes against the same target:
  baseline: propose -> execute -> keep/discard
  prae:     propose -> rebut -> pre-audit -> execute -> post-audit -> verdict

Usage:
  python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode prae
  python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode baseline
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from prae.objective import load_objective, Objective
from prae.ledger import LedgerEntry, append_entry, read_entries
from prae.executor import run_target, parse_metric
from prae.git_ops import (
    current_ref, ensure_branch, commit_file, revert_to,
    create_branch, is_clean, changed_files,
)
from prae.llm import chat_or_stub
from prae.prompts import propose, rebut, pre_audit, post_audit, revise


WORK_BRANCH = "prae/work"


def _read_mutable(obj: Objective) -> str:
    """Read the contents of the (single) mutable file."""
    path = obj.repo / obj.mutable_paths[0]
    if path.exists():
        return path.read_text()
    return ""


def _write_mutable(obj: Objective, content: str) -> None:
    """Write new content to the mutable file."""
    path = obj.repo / obj.mutable_paths[0]
    path.write_text(content)


def _history_summary(entries: list[LedgerEntry], last_n: int = 5) -> str:
    """Summarize recent ledger entries for prompt context."""
    if not entries:
        return "(no previous iterations)"
    recent = entries[-last_n:]
    lines = []
    for e in recent:
        lines.append(
            f"Iter {e.iteration}: verdict={e.verdict}, metric={e.parsed_metric}, "
            f"status={e.execution_status}"
        )
    return "\n".join(lines)


def _parse_json_response(text: str) -> dict:
    """Best-effort JSON extraction from LLM response."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": text, "patch": "", "raw": text}


def _is_improved(old: float | None, new: float | None, goal: str, threshold: float | None = None) -> bool:
    """Check if the new metric is better than the old one."""
    if old is None or new is None:
        return False
    if goal == "minimize":
        delta = old - new
    else:
        delta = new - old
    if threshold is not None:
        return delta >= threshold
    return delta > 0


def _enforce_mutable_surface(obj: Objective) -> bool:
    """Check that only allowed files have been modified."""
    changed = changed_files(obj.repo)
    for f in changed:
        if not obj.is_mutable(f):
            return False
    return True


def _get_baseline_metric(obj: Objective) -> float | None:
    """Run the target once to establish baseline metric."""
    result = run_target(obj.run_command, obj.repo, obj.budget_seconds)
    output = result.stdout + "\n" + result.stderr
    return parse_metric(output, obj.metric_regex)


def run_baseline_iteration(
    obj: Objective,
    iteration: int,
    entries: list[LedgerEntry],
    baseline_ref: str,
    baseline_metric: float | None,
    ledger_path: Path,
    dry_run: bool = False,
) -> tuple[str, float | None]:
    """Run one baseline iteration: propose -> execute -> keep/discard."""
    timestamp = datetime.now(timezone.utc).isoformat()
    current_code = _read_mutable(obj)
    history = _history_summary(entries)

    # Propose
    print(f"  [baseline] Proposing change...")
    msgs = propose(obj, current_code, history)
    raw = chat_or_stub(msgs, model=obj.model, provider=obj.provider, api_base=obj.api_base, dry_run=dry_run)
    proposal = _parse_json_response(raw)
    print(f"  [baseline] Proposal: {proposal.get('summary', '(no summary)')}")

    # Apply patch
    patch_content = proposal.get("patch", "")
    if patch_content and patch_content != current_code:
        _write_mutable(obj, patch_content)

    # Enforce mutable surface
    if not _enforce_mutable_surface(obj):
        print(f"  [baseline] VIOLATION: changes outside mutable surface. Reverting.")
        revert_to(obj.repo, baseline_ref)
        entry = LedgerEntry(
            iteration=iteration, mode="baseline", timestamp=timestamp,
            baseline_ref=baseline_ref, proposal_summary=proposal.get("summary", ""),
            patch_summary=patch_content[:200], run_command=obj.run_command,
            budget_seconds=obj.budget_seconds, execution_status="surface_violation",
            verdict="discard", notes="Changes outside mutable surface",
        )
        append_entry(ledger_path, entry)
        return baseline_ref, baseline_metric

    # Commit the change
    new_ref = commit_file(obj.repo, obj.mutable_paths[0], f"baseline iter {iteration}: {proposal.get('summary', 'change')[:60]}")

    # Execute
    print(f"  [baseline] Executing...")
    result = run_target(obj.run_command, obj.repo, obj.budget_seconds)
    output = result.stdout + "\n" + result.stderr
    new_metric = parse_metric(output, obj.metric_regex)

    status = "timeout" if result.timed_out else ("success" if result.returncode == 0 else "error")
    print(f"  [baseline] Status: {status}, metric: {new_metric}")

    # Keep or discard
    improved = _is_improved(baseline_metric, new_metric, obj.metric_goal, obj.improvement_threshold)
    verdict = "keep" if improved else "discard"
    print(f"  [baseline] Verdict: {verdict}")

    if verdict == "discard":
        revert_to(obj.repo, baseline_ref)
        final_ref = baseline_ref
        final_metric = baseline_metric
    else:
        final_ref = new_ref
        final_metric = new_metric

    entry = LedgerEntry(
        iteration=iteration, mode="baseline", timestamp=timestamp,
        baseline_ref=baseline_ref, proposal_summary=proposal.get("summary", ""),
        patch_summary=patch_content[:200], run_command=obj.run_command,
        budget_seconds=obj.budget_seconds, execution_status=status,
        parsed_metric=new_metric, verdict=verdict,
        baseline_advanced=(verdict == "keep"),
    )
    append_entry(ledger_path, entry)
    return final_ref, final_metric


def run_prae_iteration(
    obj: Objective,
    iteration: int,
    entries: list[LedgerEntry],
    baseline_ref: str,
    baseline_metric: float | None,
    ledger_path: Path,
    dry_run: bool = False,
) -> tuple[str, float | None]:
    """Run one PRAE iteration: propose -> rebut -> pre-audit -> execute -> post-audit -> verdict."""
    timestamp = datetime.now(timezone.utc).isoformat()
    current_code = _read_mutable(obj)
    history = _history_summary(entries)

    # Phase 1: Propose
    print(f"  [prae] Proposing change...")
    msgs = propose(obj, current_code, history)
    raw = chat_or_stub(msgs, model=obj.model, provider=obj.provider, api_base=obj.api_base, dry_run=dry_run)
    proposal = _parse_json_response(raw)
    print(f"  [prae] Proposal: {proposal.get('summary', '(no summary)')}")

    # Phase 2: Rebut
    print(f"  [prae] Rebutting proposal...")
    msgs = rebut(obj, json.dumps(proposal), current_code)
    raw = chat_or_stub(msgs, model=obj.model, provider=obj.provider, api_base=obj.api_base, dry_run=dry_run)
    rebuttal = _parse_json_response(raw)
    print(f"  [prae] Rebuttal: {rebuttal.get('summary', '(no summary)')}")

    # Check if rebuttal recommends rejection
    if rebuttal.get("recommendation") == "reject":
        print(f"  [prae] Rebuttal rejected proposal. Verdict: revert")
        entry = LedgerEntry(
            iteration=iteration, mode="prae", timestamp=timestamp,
            baseline_ref=baseline_ref, proposal_summary=proposal.get("summary", ""),
            rebuttal_summary=rebuttal.get("summary", ""),
            verdict="revert", notes="Rejected at rebuttal phase",
        )
        append_entry(ledger_path, entry)
        return baseline_ref, baseline_metric

    # Phase 3: Pre-audit
    print(f"  [prae] Pre-audit...")
    msgs = pre_audit(obj, json.dumps(proposal), json.dumps(rebuttal), current_code)
    raw = chat_or_stub(msgs, model=obj.model, provider=obj.provider, api_base=obj.api_base, dry_run=dry_run)
    pre_audit_result = _parse_json_response(raw)
    print(f"  [prae] Pre-audit: {'approved' if pre_audit_result.get('approve') else 'rejected'}")

    if not pre_audit_result.get("approve", True):
        print(f"  [prae] Pre-audit rejected. Verdict: revert")
        entry = LedgerEntry(
            iteration=iteration, mode="prae", timestamp=timestamp,
            baseline_ref=baseline_ref, proposal_summary=proposal.get("summary", ""),
            rebuttal_summary=rebuttal.get("summary", ""),
            pre_audit_summary=pre_audit_result.get("summary", ""),
            verdict="revert", notes="Rejected at pre-audit",
        )
        append_entry(ledger_path, entry)
        return baseline_ref, baseline_metric

    # Phase 4: Execute
    patch_content = proposal.get("patch", "")
    if patch_content and patch_content != current_code:
        _write_mutable(obj, patch_content)

    # Enforce mutable surface
    if not _enforce_mutable_surface(obj):
        print(f"  [prae] VIOLATION: changes outside mutable surface. Reverting.")
        revert_to(obj.repo, baseline_ref)
        entry = LedgerEntry(
            iteration=iteration, mode="prae", timestamp=timestamp,
            baseline_ref=baseline_ref, proposal_summary=proposal.get("summary", ""),
            rebuttal_summary=rebuttal.get("summary", ""),
            pre_audit_summary=pre_audit_result.get("summary", ""),
            execution_status="surface_violation", verdict="revert",
            notes="Changes outside mutable surface",
        )
        append_entry(ledger_path, entry)
        return baseline_ref, baseline_metric

    new_ref = commit_file(obj.repo, obj.mutable_paths[0], f"prae iter {iteration}: {proposal.get('summary', 'change')[:60]}")

    print(f"  [prae] Executing...")
    result = run_target(obj.run_command, obj.repo, obj.budget_seconds)
    output = result.stdout + "\n" + result.stderr
    new_metric = parse_metric(output, obj.metric_regex)

    status = "timeout" if result.timed_out else ("success" if result.returncode == 0 else "error")
    print(f"  [prae] Status: {status}, metric: {new_metric}")

    # Phase 5: Post-audit
    print(f"  [prae] Post-audit...")
    msgs = post_audit(obj, json.dumps(proposal), baseline_metric, new_metric, output, current_code)
    raw = chat_or_stub(msgs, model=obj.model, provider=obj.provider, api_base=obj.api_base, dry_run=dry_run)
    post_audit_result = _parse_json_response(raw)
    verdict = post_audit_result.get("verdict", "revert")

    # Validate verdict
    valid_verdicts = {"keep", "revert", "revise", "branch", "escalate"}
    if verdict not in valid_verdicts:
        verdict = "revert"

    print(f"  [prae] Verdict: {verdict}")
    print(f"  [prae] Post-audit: {post_audit_result.get('summary', '')}")

    # Act on verdict
    final_ref = baseline_ref
    final_metric = baseline_metric
    branch_name = ""

    if verdict == "keep":
        final_ref = new_ref
        final_metric = new_metric
    elif verdict == "revert":
        revert_to(obj.repo, baseline_ref)
    elif verdict == "revise":
        revert_to(obj.repo, baseline_ref)
        # revise is a signal; next iteration will call revise prompt if the loop checks
    elif verdict == "branch":
        branch_name = f"prae/branch-iter-{iteration}"
        create_branch(obj.repo, branch_name)
        revert_to(obj.repo, baseline_ref)
        print(f"  [prae] Branch saved: {branch_name}")
    elif verdict == "escalate":
        print(f"  [prae] ESCALATED — stopping for human review.")
        revert_to(obj.repo, baseline_ref)

    entry = LedgerEntry(
        iteration=iteration, mode="prae", timestamp=timestamp,
        baseline_ref=baseline_ref, proposal_summary=proposal.get("summary", ""),
        rebuttal_summary=rebuttal.get("summary", ""),
        pre_audit_summary=pre_audit_result.get("summary", ""),
        patch_summary=patch_content[:200], run_command=obj.run_command,
        budget_seconds=obj.budget_seconds, execution_status=status,
        parsed_metric=new_metric,
        post_audit_summary=post_audit_result.get("summary", ""),
        verdict=verdict, baseline_advanced=(verdict == "keep"),
        branch_name=branch_name,
    )
    append_entry(ledger_path, entry)

    return final_ref, final_metric


def run(
    objective_path: str,
    mode: str = "prae",
    ledger_path: str | None = None,
    dry_run: bool = False,
) -> None:
    """Main entry point: run the loop."""
    obj = load_objective(objective_path)
    if ledger_path is None:
        ledger_path = str(obj.repo / "ledger.jsonl")
    ledger = Path(ledger_path)

    print(f"PRAE v1 — mode: {mode}")
    print(f"  objective: {obj.name}")
    print(f"  repo: {obj.repo}")
    print(f"  mutable: {obj.mutable_paths}")
    print(f"  metric: {obj.metric_name} ({obj.metric_goal})")
    print(f"  budget: {obj.budget_seconds}s per iteration")
    print(f"  max iterations: {obj.max_iterations}")
    if dry_run:
        print(f"  DRY RUN: using stub LLM responses")
    print()

    # Set up work branch
    ensure_branch(obj.repo, WORK_BRANCH)
    baseline_ref = current_ref(obj.repo)

    # Get initial baseline metric
    print("Establishing baseline metric...")
    baseline_metric = _get_baseline_metric(obj)
    print(f"  Baseline metric: {baseline_metric}")
    print()

    entries = read_entries(ledger)

    for i in range(1, obj.max_iterations + 1):
        print(f"=== Iteration {i}/{obj.max_iterations} ===")

        if mode == "baseline":
            baseline_ref, baseline_metric = run_baseline_iteration(
                obj, i, entries, baseline_ref, baseline_metric, ledger, dry_run=dry_run,
            )
        elif mode == "prae":
            baseline_ref, baseline_metric = run_prae_iteration(
                obj, i, entries, baseline_ref, baseline_metric, ledger, dry_run=dry_run,
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")

        entries = read_entries(ledger)
        print(f"  Current best metric: {baseline_metric}")
        print()

        # Check for escalate verdict
        if entries and entries[-1].verdict == "escalate":
            print("Escalated. Stopping.")
            break

    print("Done.")
    print(f"  Final metric: {baseline_metric}")
    print(f"  Ledger: {ledger}")


def main():
    parser = argparse.ArgumentParser(description="PRAE: Propose, Rebut, Audit, Execute")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run the PRAE loop")
    run_parser.add_argument("--objective", required=True, help="Path to objective.yaml")
    run_parser.add_argument("--mode", choices=["baseline", "prae"], default="prae", help="Loop mode")
    run_parser.add_argument("--ledger", help="Path to ledger.jsonl (default: <repo>/ledger.jsonl)")
    run_parser.add_argument("--dry-run", action="store_true", help="Use stub LLM responses for testing")

    args = parser.parse_args()

    if args.command == "run":
        run(args.objective, mode=args.mode, ledger_path=args.ledger, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
