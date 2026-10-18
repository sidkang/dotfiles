Hammerspoon Configuration

- Hammerspoon configuration resides in `hammerspoon/`, and the entrypoint is `hammerspoon/init.lua`.
- `hammerspoon/init.lua` SHOULD stay focused on bootstrap and orchestration; feature logic SHOULD live in modules.
- New active modules SHOULD live in `hammerspoon/sids/`.
- Temporarily disabled or historical modules SHOULD live in `hammerspoon/inactive/`.
- Reference scripts, drafts, and demos SHOULD live in `hammerspoon/others/`.
- New top-level Lua files SHOULD be avoided; place them in `hammerspoon/sids/`, `hammerspoon/inactive/`, or `hammerspoon/others/` instead.

Loaded Modules
- `hammerspoon/init.lua` currently loads `sids.applescript`, `sids.ime`, `sids.bob`, `sids.whichkey`, `sids.console-toolbar`, `sids.daily_tasks`, `sids.clipboard`, `sids.color_meter`, `sids.float_window`, `sids.aerospace_window_hints`, `sids.audio_device`, and `sids.wallpaper`.
- When documenting active modules, treat the load list in `hammerspoon/init.lua` as the source of truth.

Module Conventions
- Feature modules SHOULD expose an explicit `setup(...)` entrypoint instead of relying on `require(...)` side effects.
- URL scheme modules will usually use `setup(route)`.
- Watcher, timer, UI, and toolbar modules will usually use `setup()`.
- Modules SHOULD stay as self-contained as practical and SHOULD avoid depending on other custom modules unless there is a clear need.
- Runtime objects such as watcher, timer, canvas, eventtap, and hotkey instances SHOULD live in module-level state.
- Setup logic SHOULD be idempotent when possible so reloading does not duplicate bindings or watchers.
- Route parameters SHOULD be validated before actions run, and failure paths SHOULD surface errors instead of failing silently.
