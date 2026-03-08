"""Prompt templates for each PRAE phase.

Each function returns a list of messages suitable for chat completion.
Role separation is done via system prompts, even when the same model handles all phases.
"""

from prae.objective import Objective


def _read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return "(file not found)"


def _context_block(obj: Objective, current_code: str, history: str = "") -> str:
    parts = [
        f"Objective: {obj.name}",
        f"Metric: {obj.metric_name} (goal: {obj.metric_goal})",
        f"Mutable file(s): {', '.join(obj.mutable_paths)}",
        f"Run command: {obj.run_command}",
        f"Budget: {obj.budget_seconds}s",
    ]
    if obj.instructions:
        parts.append(f"Instructions: {obj.instructions}")
    if history:
        parts.append(f"Previous iterations:\n{history}")
    parts.append(f"Current code:\n```python\n{current_code}\n```")
    return "\n".join(parts)


def propose(obj: Objective, current_code: str, history: str = "") -> list[dict[str, str]]:
    """Generate a proposal for improving the mutable surface."""
    ctx = _context_block(obj, current_code, history)
    return [
        {"role": "system", "content": (
            "You are a PROPOSE agent. Your job is to suggest a single, bounded code change "
            "to the mutable file that should improve the target metric.\n\n"
            "Respond in JSON with keys: summary, patch (the full new file content), "
            "expected_effect, success_criteria.\n\n"
            "Rules:\n"
            "- Only modify the mutable file(s) listed.\n"
            "- The change must be small and testable.\n"
            "- State a clear expected effect and success criterion.\n"
            "- Output valid JSON only, no markdown fences."
        )},
        {"role": "user", "content": ctx},
    ]


def rebut(obj: Objective, proposal: str, current_code: str) -> list[dict[str, str]]:
    """Challenge a proposal before it runs."""
    ctx = _context_block(obj, current_code)
    return [
        {"role": "system", "content": (
            "You are a REBUT agent. Your job is to challenge a proposed code change.\n\n"
            "Look for:\n"
            "- Flawed reasoning or unsupported assumptions\n"
            "- Risk of worsening the metric\n"
            "- Changes that are too broad or unbounded\n"
            "- Missing rollback considerations\n\n"
            "Respond in JSON with keys: summary, concerns (list of strings), "
            "recommendation ('proceed', 'revise', or 'reject').\n"
            "Output valid JSON only, no markdown fences."
        )},
        {"role": "user", "content": f"{ctx}\n\nProposal:\n{proposal}"},
    ]


def pre_audit(obj: Objective, proposal: str, rebuttal: str, current_code: str) -> list[dict[str, str]]:
    """Pre-execution audit: should this proposal run?"""
    ctx = _context_block(obj, current_code)
    return [
        {"role": "system", "content": (
            "You are a PRE-AUDIT agent. Decide whether this proposal should be executed.\n\n"
            "Check:\n"
            "1. Is the proposal bounded? (small, specific change)\n"
            "2. Does it only modify the allowed mutable surface?\n"
            "3. Are success criteria defined?\n"
            "4. Does a rollback path exist?\n"
            "5. Is the run worth the budget?\n\n"
            "Consider the rebuttal's concerns.\n\n"
            "Respond in JSON with keys: bounded (bool), only_mutable_surface (bool), "
            "success_criteria_defined (bool), rollback_path_exists (bool), "
            "worth_budget (bool), approve (bool), summary.\n"
            "Output valid JSON only, no markdown fences."
        )},
        {"role": "user", "content": f"{ctx}\n\nProposal:\n{proposal}\n\nRebuttal:\n{rebuttal}"},
    ]


def post_audit(
    obj: Objective,
    proposal: str,
    old_metric: float | None,
    new_metric: float | None,
    execution_output: str,
    current_code: str,
) -> list[dict[str, str]]:
    """Post-execution audit: what verdict should we assign?"""
    ctx = _context_block(obj, current_code)
    metric_info = f"Old metric: {old_metric}, New metric: {new_metric}"
    return [
        {"role": "system", "content": (
            "You are a POST-AUDIT agent. Evaluate the result of an executed proposal.\n\n"
            "Decide:\n"
            "1. Is the metric movement meaningful?\n"
            "2. Does the result match the proposal's expected mechanism?\n"
            "3. Is there narrative laundering (claiming success from noise)?\n\n"
            "Assign a verdict from: keep, revert, revise, branch, escalate.\n"
            "- keep: accept the change into the baseline\n"
            "- revert: undo and return to prior baseline\n"
            "- revise: reject but generate a tighter follow-up proposal\n"
            "- branch: preserve as an alternate path\n"
            "- escalate: stop for human review\n\n"
            "Respond in JSON with keys: metric_movement_meaningful (bool), "
            "matches_expected_mechanism (bool), narrative_laundering (bool), "
            "verdict (string), summary.\n"
            "Output valid JSON only, no markdown fences."
        )},
        {"role": "user", "content": (
            f"{ctx}\n\nProposal:\n{proposal}\n\n{metric_info}\n\n"
            f"Execution output (last 2000 chars):\n{execution_output[-2000:]}"
        )},
    ]


def revise(obj: Objective, proposal: str, rebuttal: str, post_audit_summary: str, current_code: str, history: str = "") -> list[dict[str, str]]:
    """Generate a tighter follow-up proposal after a 'revise' verdict."""
    ctx = _context_block(obj, current_code, history)
    return [
        {"role": "system", "content": (
            "You are a REVISE agent. A previous proposal was not accepted.\n"
            "Generate a tighter, more targeted follow-up proposal that addresses "
            "the concerns raised.\n\n"
            "Respond in JSON with keys: summary, patch (the full new file content), "
            "expected_effect, success_criteria.\n"
            "Output valid JSON only, no markdown fences."
        )},
        {"role": "user", "content": (
            f"{ctx}\n\nPrevious proposal:\n{proposal}\n\n"
            f"Rebuttal:\n{rebuttal}\n\nPost-audit:\n{post_audit_summary}"
        )},
    ]
