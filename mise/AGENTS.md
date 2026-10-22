# Mise

## Tasks

- Prefer file tasks under `mise/tasks/` for new or substantially revised non-trivial tasks. Existing long inline scripts in `mise/config.toml` are legacy, not a pattern to copy; keep new inline entries to short dispatchers or wrappers.
- Task paths should match their names, e.g. `mise/tasks/py/init` for `py:init`.
- Keep task resources beside the script, with short, descriptive names such as `sample.toml`.

## Paths

- Locate adjacent resources via `MISE_TASK_FILE`, falling back to `__file__` for direct execution.
- Project file lookup SHOULD start from `MISE_ORIGINAL_CWD`; it MUST NOT assume `PWD` is the user's project directory.
- Generated project `mise.toml` templates should use `config_root` rather than `cwd` for project-relative paths.
