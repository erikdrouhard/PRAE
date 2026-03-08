# PRAE Design Document

## ARRC Lineage

PRAE grows from the same root as ARRC: the conviction that AI systems need structured adversarial reasoning to be reliable. ARRC explores this as a reasoning framework — rebuttal-augmented generation, audit trails, confidence calibration. PRAE takes one specific claim from that space and tests it as a runtime:

**Claim**: Under the same bounded budget, the same mutable surface, and the same metric, a loop that does `propose → rebut → audit → execute → audit → verdict` should search more intelligently than a simple `edit → run → keep/discard` loop.

## Why a Separate Repo

ARRC is a reasoning framework. PRAE is an execution runtime. Mixing them would force ARRC to carry operational concerns (subprocess management, git integration, budget enforcement) and force PRAE to carry philosophical abstractions it doesn't need yet. The relationship is: ARRC provides the intellectual foundation, PRAE proves a specific thesis from that foundation.

## Why v1 Is Intentionally Narrow

Every generalization in v1 is a lie about what has been validated. PRAE v1 proves itself against one adapter (autoresearch-style code/training loops), one mutable surface (train.py), and one metric. If the thesis holds there, it earns the right to expand.

Non-goals for v1:
- Multi-domain adapters
- Web UI
- Databases
- Async orchestration
- Distributed execution
- Memory systems beyond the ledger
- Benchmark dashboards
- Autonomous branch forests

## The Core Differentiator: Audit Happens Twice

This is the architectural bet. Most experiment loops evaluate only after execution. PRAE evaluates twice:

### Pre-Execution Audit

Before spending budget, the pre-audit checks:
1. **Boundedness**: Is the proposed change small and specific?
2. **Surface compliance**: Does it only modify allowed files?
3. **Success criteria**: Are expected outcomes defined?
4. **Rollback path**: Can we cleanly undo this?
5. **Budget worthiness**: Is this run worth the compute?

This prevents the loop from wasting budget on poorly-formed experiments.

### Post-Execution Audit

After execution, the post-audit evaluates:
1. **Metric movement**: Is the change meaningful, not noise?
2. **Mechanism match**: Does the result match what was predicted?
3. **Narrative laundering**: Is the loop fooling itself?

This prevents the loop from accepting changes for bad reasons.

## The Verdict Vocabulary

Binary keep/discard loses information. PRAE's five verdicts capture more:

| Verdict | Meaning |
|---------|---------|
| **keep** | Accept into the active baseline |
| **revert** | Undo and return to prior baseline |
| **revise** | Reject, but generate a tighter follow-up |
| **branch** | Preserve as an alternate path |
| **escalate** | Stop for human review |

`revise` is particularly important: it means "the direction was interesting but the execution was wrong — try again with tighter constraints." This is strictly more informative than discard.

`branch` acknowledges that not all progress is linear. Sometimes an experiment is interesting without being immediately better.

`escalate` is the safety valve. The loop can recognize when it's confused.

## Implementation Architecture

### The Kernel

Three conceptual pieces:
- `loop.py`: the runtime — drives both modes
- `objective.yaml`: the human control point — defines what to optimize
- `ledger.jsonl`: the record — captures every cycle

### Support Modules

- `llm.py`: thin wrapper around OpenAI-compatible chat API
- `executor.py`: run a command under a time budget, parse metrics
- `git_ops.py`: commit, revert, branch via git CLI
- `prompts.py`: prompt templates for each phase (propose, rebut, pre-audit, post-audit, revise)
- `objective.py`: load and validate the objective file

### Mode Comparison

**Baseline mode** (control):
```
for each iteration:
    propose a change (LLM)
    apply it
    execute the target
    parse metric
    if improved: keep
    else: discard (revert)
```

**PRAE mode** (treatment):
```
for each iteration:
    propose a change (LLM)
    rebut the proposal (LLM)
    if rejected: skip
    pre-audit (LLM)
    if not approved: skip
    apply the change
    execute the target
    parse metric
    post-audit: assign verdict (LLM)
    act on verdict: keep/revert/revise/branch/escalate
```

Both run against the same target, same budget, same metric. The only difference is cognitive overhead per iteration.

### Git Discipline

- All work happens on a `prae/work` branch
- Each applied change is committed before execution
- `revert` = `git reset --hard` to previous known-good ref
- `branch` = create a named branch at current HEAD, then revert
- `keep` = advance the baseline ref forward

Simple and reliable. No elaborate branch management.

### Mutable Surface Enforcement

After applying a patch and before committing, the runtime checks `git diff` to verify only allowed files changed. Violations are immediately reverted.

## Future Architecture (Not v1)

These are directions, not commitments:

- **Multi-adapter support**: PRAE against hyperparameter tuning, prompt engineering, configuration optimization
- **Parallel proposals**: multiple proposals evaluated concurrently
- **Persistent memory**: ledger-derived heuristics that improve proposals over time
- **Branch forests**: systematic exploration of divergent paths
- **Human-in-the-loop UI**: for escalation and branch comparison
- **Multi-model routing**: different models for different phases (cheap rebuttals, expensive proposals)

Each of these must earn itself against the same criterion: does it make the loop search more intelligently under the same budget?
