# Dotfiles history workflow

- This setup uses mise's tracked-file history, not a source checkout. Edit the native files listed in `~/.config/mise/conf.d/dotfiles.toml`.
- Current application scope is Bat and Starship only. The shared mise module and these maintenance documents are tracked to reproduce and explain that setup.
- Use `mise dot history diff`, `mise dot save`, `mise dot history`, `mise dot sync`, and `mise dot pull` for version operations. Do not introduce JJ or run Git mutations against mise's internal history store. Read-only history inspection and secret scanning are allowed.
- The intended remote is public: `https://github.com/sidkang/dotfiles.git`, branch `master`. Do not connect or publish without explicit approval: `mise dot origin set` performs an initial synchronization even with `--sync manual`.
- Keep `history.sync = "manual"`. Do not install a watcher or enable automatic publishing without an explicit request.
- Never track the entire mise configuration directory, home directory, credentials, caches, logs, sessions, or recovery keys. Review explicit enrollment before saving. Configure encryption before the first save of any sensitive file.
- Review all history to be published, not only the latest files. Never bypass plaintext-history protections.
- Use `mise -C ~ bootstrap --only packages,dotfiles,task` for this setup. Preview first; unrelated global tools are outside this migration.
- Preview rollback, adoption, and conflict resolutions. Do not use force, blanket remote selection, or history replacement without approval.
- The legacy Stow source and archived source checkout are rollback material, not parallel sources to edit or deploy.
- Preserve Catppuccin's MIT license at `~/.config/bat/LICENSE.catppuccin`.
- This setup is not a full-system backup. Keep recovery material outside the public history.
