# Implementation Notes

## Key Assumptions

1. **Single-model sequential phases**: v1 uses the same LLM for all phases (propose, rebut, pre-audit, post-audit, revise). Role separation is done through system prompts, not separate model instances. This is intentional — it isolates the value of structured phases from the value of multi-model diversity.

2. **Git as rollback mechanism**: All reversibility runs through git. This means the target repo must be a git repo, and PRAE must have permission to commit, branch, and reset. This is the simplest reliable rollback mechanism for file-level changes.

3. **Metric via stdout regex**: The target run_command must print its metric to stdout in a format matchable by a regex with one capture group. This is simple but fragile — if the output format changes, the regex breaks. For v1, this is acceptable. A future version could support structured output (JSON, etc.).

4. **Wall-clock budget**: Budget is enforced as wall-clock seconds via `subprocess.timeout`. This is coarse but universal. It doesn't account for variable system load, but it prevents runaway executions.

5. **LLM JSON output**: All prompts request JSON output. The runtime does best-effort JSON parsing with a fallback to treating the raw text as the summary. This is pragmatic — LLMs sometimes wrap JSON in markdown fences or add commentary.

## Tradeoffs

### Why not multi-agent concurrency?
Sequential phases with the same model are simpler to debug, cheaper to run, and sufficient to prove the thesis. If the structured loop wins against baseline even with sequential same-model phases, the thesis is strong.

### Why git CLI and not GitPython or libgit2?
Fewer dependencies, easier to debug, and `git` is universally available. The operations needed (commit, reset, branch) are simple enough that subprocess calls are reliable.

### Why JSONL for the ledger?
Append-only, line-oriented, trivially parseable, no database dependency. Each iteration adds one line. The entire history is human-readable with `cat`. For v1, this is ideal.

### Why OpenAI-compatible API only?
One interface that covers OpenAI, Azure OpenAI, Ollama, vLLM, LiteLLM, and most other providers via `api_base`. Adding a second provider abstraction would be premature until there's a concrete need.

### Why `revise` doesn't loop indefinitely
The `revise` verdict reverts the change and signals the loop to try again. But it still counts against `max_iterations`. This prevents infinite revision loops. A future version could add a `max_revisions_per_iteration` limit.

### Why `branch` is minimal
In v1, `branch` creates a named git branch and records it in the ledger. It doesn't manage branch forests, compare branches, or merge them. This is enough to preserve interesting alternatives without building a branch management system.

### Why `escalate` stops the loop
`escalate` means "I'm confused — ask a human." In v1, this simply stops the loop and prints a message. A future version could integrate with a notification system or human-in-the-loop UI.

## What's Not Here

- **No persistent memory**: The ledger is a record, not a knowledge base. The LLM sees recent history via prompt context, but there's no retrieval or summarization system.
- **No parallel proposals**: Each iteration generates one proposal. Parallelism is a future optimization.
- **No cost tracking**: LLM API costs are not tracked. For v1, the user manages their own budget.
- **No Windows support**: Tested on Unix-like systems only. The subprocess and git operations should work on Windows but haven't been validated.

## Testing Strategy

Tests focus on mechanics, not LLM quality:
- Metric parsing: does the regex extract the right number?
- Mutable surface enforcement: does the guard catch violations?
- Ledger I/O: does write-then-read roundtrip?
- Git rollback: does revert return to the expected state?
- Dry-run integration: does the full loop complete with stub responses?

LLM output quality is not tested because it depends on model behavior that changes across versions and providers.
