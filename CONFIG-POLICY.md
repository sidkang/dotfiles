# 配置管理偏好

检查 `~/.config` 是否有遗漏时，先查看本文和 `mise.toml`。本文记录用户已决定的范围，不是 mise 的自动忽略规则。

已决定不纳管的程序，不再作为遗漏重复建议；只有用户要求重新评估时才调整。未列出的程序仍属待决定，不能默认忽略。

## 已纳管

- **JJ**：只管理 `~/.config/jj/config.toml`；`jj/repos/` 是本机仓库配置和状态，不纳管。
- **Yazi**：管理 `~/.config/yazi/` 的配置和主题。现有 `theme.toml` 引用的 `Catppuccin-latte.tmTheme` 在纳管时已缺失，暂保留原配置。

具体部署范围以 `mise.toml` 为准。

## 明确不纳管

| 程序 | 路径 | 决定 |
|---|---|---|
| GitHub CLI | `~/.config/gh/` | 没有必要纳管，保留本机配置。 |
| Jupyter / JupyterLab | `~/.config/jupyter/` | 暂时不纳管，包括用户设置和工作区。 |
| Colab CLI | `~/.config/colab-cli/` | 不纳管。 |
| DSH | `~/.config/dsh/` | 不纳管，包括设置和 profiles。 |

这些决定不代表删除软件或本机文件。

## 已停用或删除

- **herdr**：已卸载 Homebrew 软件，删除 `~/.config/herdr/` 和 `~/.local/state/herdr/`。不安装、不部署；若再次发现，应提示残留或重新安装，而不是建议纳管。
- **tmux**：仓库 `tmux/` 仅归档，不默认安装或部署。

## 本机私有数据与运行状态

凭据、密钥、会话、日志、缓存、数据库、锁文件和自动备份不作为配置遗漏建议纳管。混合保存配置与凭据的文件必须先检查、拆分或脱敏，不能直接复制进公开仓库。

现有本机例外继续保留：`~/.config/mise/config.local.toml`、`~/.config/nvim/lazy-lock.json`、Fish `fish_variables`。应用安装的补全和第三方依赖优先通过安装步骤复现，不直接收录本机副本。
