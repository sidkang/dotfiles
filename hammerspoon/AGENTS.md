# Hammerspoon

- `init.lua` SHOULD focus on bootstrap and orchestration; it is the source of truth for enabled modules. Feature logic belongs in modules.
- Use `sids/` for active modules, `inactive/` for disabled or historical modules, and `others/` for drafts, demos, and references. Avoid new top-level Lua files.

## Modules

- Feature modules SHOULD expose `setup(...)` rather than rely on `require(...)` side effects: typically `setup(route)` for URL handlers and `setup()` for watchers, timers, and UI.
- Modules SHOULD stay self-contained where practical; avoid other custom module dependencies unless needed.
- Runtime objects (watchers, timers, canvases, eventtaps, hotkeys) SHOULD live in module-level state.
- Setup SHOULD be idempotent when possible so reloading does not duplicate bindings or watchers.
- Modules SHOULD validate route parameters before acting and report failures.
