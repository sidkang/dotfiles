## Engineering Defaults

- Choose the simplest implementation that fully satisfies requirements and preserves contracts.
- Design deep modules.
- Introduce an abstraction only when it simplifies the current implementation, removes demonstrated duplication, or represents a current domain boundary.
- If `.jj/` exists, use `jj` rather than `git` for version-control operations.

## Subagents

- Agent types set default thinking levels. For very hard tasks, raise the level with a `:thinking` suffix on the `agent_spawn` model, e.g. `claude/opus-5.5:high`.
