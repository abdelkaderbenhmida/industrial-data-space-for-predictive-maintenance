# Project Rules

Rules all agents follow when working in this repo. Read this before starting
any task.

## Conventions
- Follow the existing code style and patterns in the repo. Match what is there.
- Do not add comments unless asked.
- Keep changes scoped to your assigned task.

## Structure
- `docs/PRD.md` — product requirements (source of truth)
- `docs/TECHNICAL.md` — technical spec and architecture
- `docs/TASKS.md` — TaskList with status (`[x]`, `[~]`, `[!]`)

## Workflow
- Work in your assigned git worktree; commit to your agent branch.
- Update your scratchpad at `.worktrees/.scratchpad/<name>.md`.
- Before starting, read sibling scratchpads for dependencies/blockers.
- Verify your work (tests/build) before declaring a task done.

## Verification
- Run the project's test suite and linters after changes.
