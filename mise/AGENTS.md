Mise Configuration
- Mise configuration resides in `mise/`.
- Non-trivial task implementations SHOULD prefer file tasks under `mise/tasks/` instead of embedding long scripts in `mise/config.toml`.
- Existing inline tasks in `mise/config.toml` are legacy exceptions during migration and MUST NOT be treated as the preferred pattern for new complex tasks.
- When adding or substantially revising a complex task, prefer moving the implementation into `mise/tasks/` rather than extending inline shell blocks in `mise/config.toml`.
- Small dispatch or wrapper tasks in `mise/config.toml` are fine when they stay short and mainly forward to a file task.
- File task paths SHOULD express the task name directly, e.g. `mise/tasks/py/init` for the `py:init` task.

Task Resources
- Task-specific resource files SHOULD live next to the task implementation, e.g. `mise/tasks/py/sample.toml`.
- A file task SHOULD locate its own adjacent resources from `MISE_TASK_FILE`, with `__file__` as a fallback for direct script execution.
- A file task that operates on the user's current project SHOULD locate project files from `MISE_ORIGINAL_CWD` instead of relying on the default `PWD`.
- Mise file tasks MUST NOT assume the default working directory is the target project directory.

Generated Project Config
- When generating content for a project's `mise.toml`, project-relative template logic SHOULD prefer `config_root` over `cwd`.
- Sample file names SHOULD stay short and descriptive once they are separated from `mise/config.toml`, e.g. `sample.toml`.
