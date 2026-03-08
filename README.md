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
# Install PRAE
pip install -e .

# Dry run (no API key needed — uses stub LLM responses)
python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode prae --dry-run
python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode baseline --dry-run
```

To run against a real target:

```bash
# 1. Set up your target repo (must be a git repo with a train.py on main)
cd /path/to/your/target-repo
git init && git add train.py && git commit -m "initial"

# 2. Copy and edit the objective to point at your target
cp examples/autoresearch/objective.yaml my_objective.yaml
# Edit my_objective.yaml: set repo_path, run_command, metric_regex, etc.

# 3. Run
export OPENAI_API_KEY=sk-...
python -m prae.loop run --objective my_objective.yaml --mode baseline
python -m prae.loop run --objective my_objective.yaml --mode prae
```

PRAE creates a `prae/work` branch from `baseline_ref` in your target repo. All mutations happen there. Your `main` branch is never touched.

## What You Need

1. A target repo with a `train.py`
2. A `run_command` that prints a metric to stdout
3. An `objective.yaml` defining the contract

For v1, `train.py` is the only mutable surface. Everything else is immutable.

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

## Results

v1 proving ground: a small neural net training loop (`train.py`), minimizing loss, 5 iterations, 120s budget per iteration.

| | Baseline | PRAE |
|---|---|---|
| Iterations used | — | — |
| Final metric | — | — |
| Proposals rejected pre-execution | n/a | — |
| Verdicts: keep / revert / revise | — / — / n/a | — / — / — |

*Table will be filled after the first real benchmark run. Both modes run against the same target, same budget, same metric — the only variable is loop structure.*

To reproduce:
```bash
export OPENAI_API_KEY=sk-...
python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode baseline
python -m prae.loop run --objective examples/autoresearch/objective.yaml --mode prae
```

## Credits and Lineage

PRAE's proving-ground approach — point an LLM at a training script, run it, parse a metric, keep or discard — is directly inspired by Andrej Karpathy's [autoresearch](https://github.com/karpathy/autoresearch). PRAE wraps that same loop with structured rebuttal and double audit to test whether the added cognition is worth it.

The deeper intellectual foundation comes from [ARRC](https://github.com/erikdrouhard/ARRC-loop)'s reasoning lineage — the idea that structured adversarial reasoning makes AI systems more reliable. PRAE is a separate repo because it tests a different thesis: that these ideas work as a *runtime loop*, not just a reasoning framework.

## License

MIT
