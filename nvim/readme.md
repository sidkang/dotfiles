# nvim

Neovim 配置，部署见[根 README](../README.md)。插件配置在 `lua/plugins/`；需要 Lean 时，在 `lua/plugins/lean.lua` 设置 `enabled = true`。

## 工具

Mason 管理 LSP 与 formatter。Caddyfile / TOML 格式化另需 `caddy` / `taplo`；`joker` 是 `cljfmt` 的可选后备，`fish_indent` 随 Fish 提供。

## 按键

- `<leader>s*`：search / picker
- `<leader>se`：mini.files
- `<leader>cf`：format
- `<leader>u*`：UI toggles
- `<leader>w*`：windows / buffers
- `<leader>g*`：git / jj（mini.git；mini.diff 在 jj 仓库对比 `@-`）
- `gs*`：surround

REPL（Python / sh）：

- `<localleader>i`：选择 kitty target
- `<localleader>l/s/v`：发送 line / motion / selection
- `<localleader>c/n`：发送 cell / cell and next
- `<localleader>r/x`：向 target 发送 Enter / Ctrl-C
