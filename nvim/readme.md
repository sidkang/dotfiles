# nvim

极简 Neovim 全局配置，stow 到 `~/.config/nvim`。

## 组成

- lazy.nvim
- catppuccin
- blink.cmp
- native LSP + nvim-lspconfig
- conform.nvim
- mini.pick / mini.extra / mini.files / mini.diff / mini.clue / mini.notify
- vim-slime + kitty
- sidekick.nvim

Lean 已迁移但默认禁用；需要时在 `lua/plugins/lean.lua` 改 `enabled = true`。

## 工具

Mason 管理 LSP / formatter；少量系统工具用 Homebrew：`joker`、`caddy`、`taplo`、`fish_indent`。

## 按键

- `<leader>s*`：search / picker
- `<leader>se`：mini.files
- `<leader>c*`：code actions / format
- `<leader>u*`：UI toggles
- `<leader>w*`：windows / buffers
- `<leader>o*`：sidekick

REPL 只在 Python / sh 启用：

- `<localleader>i`：选择 kitty target
- `<localleader>l/s/v`：发送 line / motion / selection
- `<localleader>c/n`：发送 cell / cell and next
- `<localleader>r/x`：向 target 发送 Enter / Ctrl-C key event

## 状态

`lua-legacy/` 和 `after-legacy/` 已清理。
