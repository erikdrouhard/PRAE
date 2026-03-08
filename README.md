# PRAE: Propose, Rebut, Audit, Execute

A runtime for bounded experimentation under structured rebuttal.

## The Idea in 30 Seconds

**Autoresearch-style loop:**
```
edit → run → keep/discard
```

**PRAE:**
```
propose → rebut → audit → execute → audit → keep/revert/revise/branch/escalate
```

Same mutable surface. Same budget. Same metric. Different loop intelligence.

## Why This Matters

A minimal experiment loop (edit/run/keep-discard) does search. But it doesn't *think* about what it's doing. It can't challenge its own proposals before spending budget. It can't distinguish meaningful improvement from noise after the fact.

PRAE adds structured cognition to the same loop:

- **Propose**: generate a bounded change
- **Rebut**: challenge it before it runs
- **Pre-audit**: verify the change is worth the budget
- **Execute**: run it under the same constraints
- **Post-audit**: evaluate whether the result is real
- **Verdict**: keep, revert, revise, branch, or escalate

### Why Audit Happens Twice

Pre-audit catches wasted budget. Post-audit catches narrative laundering — the tendency to interpret noise as signal. Together they make the loop honest.

### Why the Verdict Vocabulary Matters

`keep/discard` is binary. PRAE's vocabulary (`keep`, `revert`, `revise`, `branch`, `escalate`) lets the loop express uncertainty, preserve alternatives, and ask for help. `revise` means "tighten and re-propose." `branch` means "this is interesting but not better — save it." `escalate` means "I don't know — human, look at this."

## Quick Start

```bash
# Install
pip install -e .

# Run in PRAE mode (dry run, no API key needed)
python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode prae --dry-run

# Run in baseline mode
python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode baseline --dry-run

# With a real LLM (set your API key)
export OPENAI_API_KEY=sk-...
python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode prae
```

## What You Need

1. A target repo with a `train.py` (or other mutable file)
2. A `run_command` that produces a metric on stdout
3. An `objective.yaml` defining the contract

## The Three-File Mental Model

```
loop.py          — the runtime
objective.yaml   — the human control point
ledger.jsonl     — the record of every cycle
```

Everything else is support.

## Repo Structure

```
prae/
  loop.py        — main runtime loop (baseline + prae modes)
  llm.py         — LLM integration (OpenAI-compatible)
  executor.py    — run target under budget
  git_ops.py     — git rollback and lineage
  ledger.py      — JSONL ledger read/write
  objective.py   — load and validate objective.yaml
  prompts.py     — prompt templates for each phase
examples/
  autoresearch/
    objective.yaml
    train.py       — example mutable target
docs/
  design.md      — deeper architecture and philosophy
tests/
```

## ARRC Lineage

PRAE is inspired by [ARRC](https://github.com/erikdrouhard/ARRC)'s reasoning lineage — the idea that structured rebuttal and audit make AI systems more reliable. PRAE is a separate repo because it tests a different thesis: that these ideas work as a *runtime loop*, not just a reasoning framework.

## License

MIT
