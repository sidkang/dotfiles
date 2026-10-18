# WhichKey Plugin SPEC

## Purpose

`whichkey.lua` is a small Hammerspoon helper that shows a delayed, floating key guide for modal shortcuts.

It is intended for workflows where another tool or hotkey layer enters a mode, waits for the next key, and wants to display an on-screen cheat sheet only if the user hesitates.

Typical usage:

- Show a guide when entering a key mode.
- Hide the guide when the mode exits or a key is handled.
- Define shortcut groups in Lua with labels and descriptions.
- Highlight important words inside descriptions with theme colors.

## Non-goals

- It does not register keyboard shortcuts.
- It does not execute actions.
- It does not manage modal state.
- It does not read external config files.
- It does not depend on other custom Hammerspoon modules.

The plugin is only a presentation layer for key guides.

## Runtime Environment

- Host: Hammerspoon on macOS.
- APIs used:
  - `hs.urlevent`
  - `hs.canvas`
  - `hs.timer`
  - `hs.screen`
  - `hs.notify`
- Suggested module name: `whichkey` or any project-local module path chosen by the host config.
- Entrypoint: `setup(route)`.

## Public API

### Lua setup

```lua
require("whichkey").setup("whichkey")
```

`setup(route)` binds a Hammerspoon URL route. The route name is configurable and becomes the URL host used by `hammerspoon://`.

### URL actions

The plugin is controlled through Hammerspoon URLs:

```text
hammerspoon://whichkey?action=show&group=<group-name>
hammerspoon://whichkey?action=hide&group=<group-name>
hammerspoon://whichkey?action=hide
```

Actions:

| Action | Params | Behavior |
| --- | --- | --- |
| `show` | `group` required | Starts a delayed show timer for the named group. |
| `hide` | `group` optional | Cancels pending show and/or hides the visible guide. Without `group`, hides everything. |

Unknown actions are ignored.

## Timing Behavior

- Showing is delayed by a configurable or module-local `showDelaySeconds` value.
- Default delay: `0.45` seconds.
- If `hide` is received before the delay expires, the guide is not shown.
- If a different group is requested before the timer fires, the older request is ignored.

This prevents UI flicker for users who press the next key quickly.

## Data Model

Shortcut guides are stored in a local `groups` table.

```lua
local groups = {
  ["group-name"] = {
    desc = "Human readable group title",
    items = {
      { key = "A", desc = "Run {Action|blue}" },
      { key = "B", desc = "Open {Browser|teal}" },
    },
  },
}
```

### Group fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `desc` | string | yes | Title shown at the top of the guide. |
| `items` | array | yes | Ordered list of key rows. |

### Item fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `key` | string | yes | Key label shown in the pill, e.g. `H`, `Shift`, `123`, `HJKL`. |
| `desc` | string | yes | Description shown next to the key. Supports inline color markup. |

## Description Markup

Item descriptions may contain inline highlighted segments:

```text
plain text {highlighted text|colorName} more text
```

Examples:

```lua
{ key = "H", desc = "Move {left|teal}" }
{ key = "R", desc = "{Reload|yellow} config" }
```

Rules:

- Markup format is `{text|color}`.
- `text` is rendered using the specified theme color.
- Plain text is rendered using the default description color.
- If no color is supplied, the segment falls back to `peach`.
- Supported color names are the Catppuccin Latte palette keys defined in the module:
  - `rosewater`, `flamingo`, `pink`, `mauve`, `red`, `maroon`, `peach`, `yellow`, `green`, `teal`, `sky`, `sapphire`, `blue`, `lavender`, `text`, `subtext1`, `subtext0`, `overlay2`, `overlay1`, `overlay0`, `surface2`, `surface1`, `surface0`, `base`, `mantle`, `crust`.

## Visual Design

The guide is a compact floating card. Default placement is near the bottom-right of the main screen.

Default visual structure:

1. Rounded translucent card.
2. Small subtitle: `KEY GUIDE`.
3. Group title.
4. Divider line.
5. Rows with:
   - key pill on the left,
   - description text on the right,
   - optional colored inline description segments.

The module uses the Catppuccin Latte palette and Hammerspoon canvas primitives only.

## Layout Rules

- Width is computed from the group title and the widest item description.
- Width is clamped between `layout.minWidth` and `layout.maxWidth`.
- Height is computed from item count and row spacing.
- Height is at least `layout.minHeight`.
- Default card position is anchored to the main screen bottom-right using `rightMargin` and `bottomMargin`.
- Text measurement uses a hidden canvas and `minimumTextSize`.

## Error Handling

If `show` is called for a missing group, the plugin sends a Hammerspoon notification:

```text
WhichKey: group not found: <group-name>
```

Missing or unknown hide targets are safe and should not error.

## Expected Integration Pattern

A modal shortcut owner should call `show` when the mode starts and `hide` when the mode ends.

Example shell commands:

```sh
open 'hammerspoon://whichkey?action=show&group=navigation'
open 'hammerspoon://whichkey?action=hide&group=navigation'
```

Example lifecycle:

1. User presses a prefix key.
2. Modal owner starts mode.
3. Modal owner opens `hammerspoon://whichkey?action=show&group=navigation`.
4. If the user presses a next key before `0.45s`, modal owner opens `hide`; no guide appears.
5. If the user hesitates, guide appears.
6. When mode exits, modal owner opens `hide`.

## Karabiner-Elements / Goku Integration

Karabiner-Elements can trigger the plugin by running shell commands that open the Hammerspoon URL. If the config is generated with Goku, define a template that expands to `open -g "hammerspoon://..."`.

Example `karabiner.edn` template:

```clojure
{:templates {:hs "open -g \"hammerspoon://%s\""}}
```

Example modal rule in `karabiner.edn`:

```clojure
{:des "navigation mode"
 :rules [[:quote
          [["navigation-mode" 1]
           [:hs "whichkey?action=show&group=navigation"]]
          nil
          {:afterup [["navigation-mode" 0]
                     [:hs "whichkey?action=hide&group=navigation"]]
           :alone :quote}]

         :navigation-mode
         [:h [:left_arrow] nil {:afterup [:hs "whichkey?action=hide&group=navigation"]}]
         [:j [:down_arrow] nil {:afterup [:hs "whichkey?action=hide&group=navigation"]}]
         [:k [:up_arrow] nil {:afterup [:hs "whichkey?action=hide&group=navigation"]}]
         [:l [:right_arrow] nil {:afterup [:hs "whichkey?action=hide&group=navigation"]}]]}
```

The important contract is only the generated URL:

```text
hammerspoon://<route>?action=show&group=<group-name>
hammerspoon://<route>?action=hide&group=<group-name>
```

Recommended pattern:

- Call `show` when a layer, simlayer, or modal prefix becomes active.
- Call `hide` on key release, mode exit, or after a mapped action runs.
- Prefer hiding without `group` if a single global guide is enough: `hammerspoon://<route>?action=hide`.

## Plugin Implementation Requirements

A compatible implementation should:

- Expose `setup(route)`.
- Bind the route using `hs.urlevent.bind`.
- Support `action=show` and `action=hide`.
- Support group lookup by string name.
- Delay rendering before showing a group.
- Cancel pending shows on hide.
- Reuse canvas objects instead of creating new windows repeatedly.
- Keep runtime objects in module-level state.
- Render without relying on other custom config modules.
- Notify when a requested group does not exist.

## Suggested LLM Build Task

When asking an LLM to build or modify this plugin, provide this spec and ask it to preserve the public URL contract.

Example prompt:

```text
Implement a Hammerspoon WhichKey plugin from SPEC.md.
Keep the public API compatible:
- require("whichkey").setup(route)
- hammerspoon://<route>?action=show&group=<name>
- hammerspoon://<route>?action=hide&group=<name>

The plugin should render a delayed floating canvas key guide from a local groups table, support inline `{text|color}` description markup, and avoid side effects until setup(route) is called.
```

## Future Extension Ideas

These are optional and should not be required for compatibility:

- Export a `registerGroup(name, group)` function.
- Load groups from a separate Lua file.
- Support multiple screen placement modes.
- Support dark/light themes.
- Add per-group custom subtitles.
- Add font configuration.
