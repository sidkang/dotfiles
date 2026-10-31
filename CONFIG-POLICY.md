# 配置管理例外

本文只记录不纳管的例外和禁止收录的数据，不是 mise 的自动忽略规则。正常部署范围以 `mise.toml` 为准；仓库内私有文件另用 `.gitignore` 防止误收录。

## 不纳管

| 程序或范围 | 路径及边界 |
|---|---|
| SSH | `~/.ssh/`，包括 config、密钥、连接历史和 agent 状态；不归档、不部署、不与仓库同步 |
| GitHub CLI | `~/.config/gh/` |
| Jupyter / JupyterLab | `~/.config/jupyter/`，包括用户设置和工作区 |
| Colab CLI | `~/.config/colab-cli/` |
| DSH | `~/.config/dsh/`，包括设置和 profiles |
| herdr | `~/.config/herdr/`、`~/.local/state/herdr/`；不安装或部署 |
| tmux | `~/.config/tmux/`、仓库 `archive/tmux/`；仅归档，不安装或部署 |
| JJ 本机仓库配置和状态 | `~/.config/jj/repos/` |
| mise 本机覆盖 | `~/.config/mise/config.local.toml` |
| Neovim 插件锁文件 | `~/.config/nvim/lazy-lock.json` |
| Fish 通用变量 | `~/.config/fish/fish_variables`，不整体纳管 |

不纳管不代表删除软件或本机文件。应用安装的补全和第三方依赖优先通过安装步骤复现，不直接收录本机副本。

## 禁止收录

- 明文凭据、私钥、认证和会话数据。经过用户确认的 age 密文配置例外；解密密钥禁止入库。
- 日志、缓存、数据库、锁文件、自动备份等运行状态。
- 混合保存配置与凭据的文件：必须先检查、拆分或脱敏，不能直接复制进公开仓库。
