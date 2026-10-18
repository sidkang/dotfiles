# Repository rules

- This is a public repository. Use jj (colocated with Git); publish through bookmark `master`.
- Each top-level directory holds one program's configuration. Root `mise.toml` holds all deployment entries, packages, and the `bootstrap` task.
- Deployed files are symlinks into this repository. Editing a source, or any jj command that rewrites `@` (rebase, new, edit, restore), changes the live configuration immediately.
- To add a program: create `<program>/`, add one `[dotfiles]` entry, and declare its package in `[bootstrap.packages]`. `symlink-each` entries exclude `README.md`, `AGENTS.md`, and `.DS_Store`. Exception: `pi/agent/AGENTS.md` is pi's global instruction file and is deployed.
- Preview with `mise dot diff` or `mise dot apply --dry-run` before `mise dot apply`. For packages and setup, use `mise bootstrap --only packages,dotfiles,task`.
- Do not use `mode = "track"`, `mise dot save/origin/sync/pull`, the history watcher, Stow, or chezmoi.
- jj snapshots every non-ignored file. Add private files, like `espanso/match/mine.yml`, to `.gitignore` before running jj. Fish secrets go only in git-ignored `fish/conf.d/secrets.fish`. Never print private files; refer to secrets by variable name. Never commit credentials, keys, sessions, logs, or caches. Before publishing, review every changed file and run gitleaks on the tree and history.
- Do not force overwrites, prune, rewrite published history, or force-push without explicit approval. Do not commit, move bookmarks, or push unless asked.
- Keep changes and verification small. Do not add tests for simple path mappings.
