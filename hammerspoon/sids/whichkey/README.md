# WhichKey

Delayed key guide for modal shortcuts. Groups come from `goku/menus.toml`; regenerate `groups.lua` with `mise run goku:gen` (do not edit it by hand).

Routes (`hs -c 'hsurl("…")'`, or `hammerspoon://…`):

- `whichkey?action=show&group=<id>`: show after 0.45 s, or replace the visible guide
- `whichkey?action=hide[&group=<id>]`: cancel or hide; with `group`, only if that group is the one showing

A guide that never receives `hide` disappears after 12 s. The card follows the system light/dark appearance.

Preview without showing: `hs -c 'require("sids.whichkey").snapshot("as-go", "/tmp/as-go.png")'`.
