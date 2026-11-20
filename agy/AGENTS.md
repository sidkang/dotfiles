## Engineering & Workflow

- Choose the simplest implementation that fully satisfies requirements and preserves contracts.
- Design deep modules. Introduce an abstraction only when it simplifies the current implementation, removes demonstrated duplication, or represents a current domain boundary.
- If `.jj/` exists, use `jj` rather than `git` for version-control operations.
- Do not invoke `python`, `python3`, or `pip` directly; use `uv` (`uv run`, `uv sync`, `uv add`, etc.) unless an existing project task specifies otherwise.
- Do not create project-local `.venv/` directories; use centralized `uv` environments (`UV_PREVIEW_FEATURES = "centralized-project-envs"` or `UV_PROJECT_ENVIRONMENT`). Respect `mise.toml` first (run via `mise exec -- uv ...` or `mise` tasks so non-interactive shells load `[env]`), or pass `--no-project` for standalone scripts.
- Deliver every requested item; if part is blocked, finish independent parts and state the specific blocker in one sentence.
- Verify changes by running or testing them; if verification cannot be run, state plainly that it was not.

## Push Back

- When the user is clearly wrong (factual error, or conflict with an earlier decision, stated goal, or existing code), say so before acting: name the problem, give the evidence, and recommend a fix. Do not silently comply or silently "fix" it.
- Once the user confirms, do it their way. Do not argue about taste.

## Swarm & Subagents

- When spawning a `swarm`, treat this as an explicit user instruction for worker model selection: keep the coordinator on the active session model, query `swarm{action:"models", all:true}`, and pick an exact variant (effort tier left to the coordinator based on the task unless noted) from:
  - `Gemini 4 Hydrogen` (default `Gemini 4 Hydrogen (High)`) for particularly simple/trivial tasks.
  - `Gemini 4 Neon` as the default for normal tasks.
  - `Gemini 4 Carbon` only for particularly hard tasks (e.g., deep reasoning/debugging where Neon is insufficient, or when Neon quota is exhausted).
- For subagents (`invoke_subagent` and `run_workflow` agents), keep the default `inherit` model.
