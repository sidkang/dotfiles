# Catppuccin Latte：官方与 Custom 版本

> 目的：保留官方 Catppuccin Latte 基线，同时把本仓库原有变体明确命名为 `custom`；区分 canonical token 改值、应用 role 重映射与应用专属额外色值。

## 官方权威来源

- Catppuccin Org 的 [`catppuccin/palette`](https://github.com/catppuccin/palette) 是官方 palette 库。下面数值取自固定提交 [`07d02aa110ef9eb7e7427afca5c73ba9cf7f8ebd`](https://github.com/catppuccin/palette/tree/07d02aa110ef9eb7e7427afca5c73ba9cf7f8ebd) 的 [`palette.json`](https://github.com/catppuccin/palette/blob/07d02aa110ef9eb7e7427afca5c73ba9cf7f8ebd/palette.json#L3-L554) 中 `latte`（该 flavor 标记为 `dark: false`）。
- Kitty 的 role 映射以固定版本的官方 [`themes/latte.conf`](https://github.com/catppuccin/kitty/blob/43098316202b84d6a71f71aaf8360f102f4d3f1a/themes/latte.conf#L10-L84) 为准。
- Starship 的 palette 字段以官方 [`themes/latte.toml`](https://github.com/catppuccin/starship/blob/main/themes/latte.toml) 为准。

| 官方 token | Latte canonical hex |
| --- | --- |
| `rosewater` | `#dc8a78` |
| `flamingo` | `#dd7878` |
| `pink` | `#ea76cb` |
| `mauve` | `#8839ef` |
| `red` | `#d20f39` |
| `maroon` | `#e64553` |
| `peach` | `#fe640b` |
| `yellow` | `#df8e1d` |
| `green` | `#40a02b` |
| `teal` | `#179299` |
| `sky` | `#04a5e5` |
| `sapphire` | `#209fb5` |
| `blue` | `#1e66f5` |
| `lavender` | `#7287fd` |
| `text` | `#4c4f69` |
| `subtext1` | `#5c5f77` |
| `subtext0` | `#6c6f85` |
| `overlay2` | `#7c7f93` |
| `overlay1` | `#8c8fa1` |
| `overlay0` | `#9ca0b0` |
| `surface2` | `#acb0be` |
| `surface1` | `#bcc0cc` |
| `surface0` | `#ccd0da` |
| `base` | `#eff1f5` |
| `mantle` | `#e6e9ef` |
| `crust` | `#dce0e8` |

## 保存的版本与当前选择

| 程序 | 官方版本 | Custom 版本 | 当前选择 |
| --- | --- | --- | --- |
| Starship | `[palettes.catppuccin_latte]` | `[palettes.catppuccin_latte_custom]` | `palette = "catppuccin_latte_custom"` |
| Pi | `themes/catppuccin-latte.json` | `themes/catppuccin-latte-custom.json` | `settings.json` 的 `theme: "catppuccin-latte-custom"` |
| Kitty | `catppuccin-latte.conf` | `catppuccin-latte-custom.conf` | `kitty.conf` include custom 文件 |

官方文件/调色板保留 `blue: #1e66f5`。Starship 的两个 palette 都保留完整的 26 个官方 token，另加本配置需要的通用 role 别名；Custom 版本的其他 canonical token 与官方一致，只有 `blue` 使用本地值 `#2d75c7`。

## Custom 蓝色的取值与影响

| token | 官方 | 旧 custom | 新 custom |
| --- | --- | --- | --- |
| `blue` | `#1e66f5` | `#3a81af` | `#2d75c7` |

新 custom 蓝相对 Latte `base`（`#eff1f5`）的对比度约为 **4.14:1**：比旧 custom 的 **3.76:1** 更醒目，但仍低于官方的 **4.34:1**。HSL 约为 `211.9° / 63.1% / 47.8%`，仍比官方 `220° / 91.5% / 53.9%` 更克制。此为针对 `base` 的静态计算，不代表所有实际 UI 组合的可访问性结论。

- Pi custom 中引用 `blue` 的 `accent`、`toolTitle`、`mdLink`、`syntaxFunction`、`thinkingMinimal` 与 `bashMode` 会使用新值。
- Kitty custom 的 ANSI `color4` / `color12` 使用新值。
- Starship custom 的 `blue` palette role 使用新值。

Pi 的 `toolPendingBg`、`toolSuccessBg`、`toolErrorBg`、`export.pageBg` 是 Pi 专属额外色值，而不是对官方 Latte token 的替换。

## Kitty 的额外 role 差异

`kitty/catppuccin-latte.conf` 是官方原样版本；`kitty/catppuccin-latte-custom.conf` 保留了原有本地 role 选择。相对官方 Kitty port，custom 文件还存在以下差异：

| role／字段 | 官方 Kitty Latte | Custom | 说明 |
| --- | --- | --- | --- |
| `color4` / `color12` | `#1e66f5` | `#2d75c7` | ANSI normal / bright blue |
| `wayland_titlebar_color` | `system` | `#eff1f5` | 固定为 Latte `base` |
| `macos_titlebar_color` | `system` | `#eff1f5` | 固定为 Latte `base` |
| `scrollbar_handle_color` | `#7c7f93` | 未声明 | 交由 Kitty 默认／其他配置决定 |
| `scrollbar_track_color` | `#bcc0cc` | 未声明 | 交由 Kitty 默认／其他配置决定 |

`kitty.conf` 使用 `tab_bar_style custom`。尽管标准 tab 声明也包含 custom blue，实际自定义 renderer `tab_bar.py` 仍使用自己的 active pink、inactive crust/overlay1 与透明背景；因此 active tab 不会因为 ANSI blue 的调整而变成蓝色。

## Sources

1. Catppuccin Org, palette repository: https://github.com/catppuccin/palette
2. 固定提交的 Latte 官方定义：https://github.com/catppuccin/palette/blob/07d02aa110ef9eb7e7427afca5c73ba9cf7f8ebd/palette.json#L3-L554
3. Catppuccin Org, Kitty port：https://github.com/catppuccin/kitty
4. 官方 Kitty Latte role 映射：https://github.com/catppuccin/kitty/blob/43098316202b84d6a71f71aaf8360f102f4d3f1a/themes/latte.conf#L10-L84
5. Catppuccin Org, Starship port：https://github.com/catppuccin/starship
6. 官方 Starship Latte palette：https://github.com/catppuccin/starship/blob/main/themes/latte.toml
