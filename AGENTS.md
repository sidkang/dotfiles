# Repository rules

- Before auditing unmanaged configuration, read `CONFIG-POLICY.md`. Do not report recorded exclusions as omissions or suggest managing them unless the user asks to reconsider. Never collect private data; ask the user about new, undecided configuration.
- Use jj (colocated with Git) in this public repository; publish through bookmark `master`.
- Root `mise.toml` declares packages, deployment entries, and bootstrap setup. To add a program, create `<program>/` and add its `[dotfiles]` and `[bootstrap.packages]` entries there.
- Most deployments are symlinks: source edits and revision changes may immediately affect live configuration. `pi/agent/subagent-manager/` uses copy mode.
- `symlink-each` entries exclude `README.md`, `AGENTS.md`, and `.DS_Store`; `pi/agent/AGENTS.md` is an exception and must be deployed.
- `tmux/` is archived; do not install or deploy it.
- Preview with `mise dot diff` or `mise dot apply --dry-run` before `mise dot apply`. For packages and setup, use `mise bootstrap --only packages,dotfiles,task`.
- Do not use `mode = "track"`, `mise dot save/origin/sync/pull`, the history watcher, Stow, or chezmoi.
- Add private files to `.gitignore` before running jj. Fish secrets belong only in git-ignored `fish/conf.d/secrets.fish`. Never print private files; refer to secrets by variable name. Never commit plaintext credentials or private keys, sessions, logs, or caches. Explicitly approved age ciphertext is allowed; decryption identities must stay outside the repository. Before publishing, review every changed file and run gitleaks on the tree and history.
- Do not force overwrites, prune, rewrite published history, or force-push without explicit approval. Do not commit, move bookmarks, or push unless asked.
- SSH sync covers only `~/.ssh/config`, never SSH private/public keys. After changing that config, run `mise ssh:save`; before publishing, run `mise ssh:check`. These tasks must not print private content or implicitly overwrite existing configuration.
- Keep changes and verification small. Do not add tests for simple path mappings.
