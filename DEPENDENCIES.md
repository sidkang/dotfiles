# 配置依赖审计

本次检查仓库内公开配置、脚本和任务，并核对本机 Homebrew 清单与命令路径。没有读取 secrets、认证、会话、解密 identity 或其他本机私密配置。已记录的不纳管范围以 `CONFIG-POLICY.md` 为准，不算遗漏。

## 安装边界

- 安装声明在各应用的 `Brewfile`；根 `mise.toml` 不安装软件。
- `<app>:install` 只安装该应用依赖；`:plan` 只预览部署；`:apply` 只部署指定目标。三者没有自动依赖。
- 必需共享依赖在各使用方重复声明。独立工具（如 gh、rbw、Go）也有自己的安装入口。
- 每个应用只有一份 `Brewfile`，包含该配置使用的依赖；不设置 optional 文件或 extras 安装任务。执行安装前审查整份清单。
- 缓存重建、应用初始化、插件更新和服务启动/重启分别显式执行。
- 禁止 mise 任务、exec 和命令缺失时自动安装。系统包只走真正的 Homebrew CLI，失败或信任检查不通过时停止。
- 检查不自动安装工具；`scripts/check-secrets.py` 只使用 Homebrew 前缀里的 gitleaks，不经 mise shim。
- 既有 Jupyter 用户配置仍不纳管。`jupyter/Brewfile` 只声明公开 `jupy:*` 任务的运行依赖。启动不再使用会下载临时环境的 `uv tool run`；显式 `jupy:setup` 使用已有 Homebrew Python，禁止 uv 自动下载 Python。`jupy:enable` 只注册已有 kernel，项目依赖安装拆为 `jupy:kernel-install`。

## 从实际调用补充的应用依赖

| 应用 | 依赖 | 依据 |
|---|---|---|
| Fish | gh、starship、zoxide | `fish/config.fish` 的交互初始化；后两项有守卫，但已确认为常用功能 |
| Kitty | fzf、jq、Python、两款字体 | `kitty/context_switcher.py`、`fish/conf.d/kitty.fish`、`kitty/kitty.conf` |
| AeroSpace | borders、Python 3.14、Fish、Hammerspoon | `aerospace/aerospace.toml` 的启动与 workspace hook、`aerospace/as.py` |
| Goku | Karabiner-Elements、borders、Python 3.14、AeroSpace、Hammerspoon、Kitty | `goku/karabiner.edn` 的窗口管理层直接调用这些应用；不会代为部署或初始化它们 |
| Hammerspoon | ImageMagick、AeroSpace | 壁纸处理及 `sids.aerospace_window_hints` 调用 |
| Neovim | Git、Fish、tree-sitter-cli、ripgrep、fd | 插件安装、Fish formatter、treesitter 构建和查找功能 |
| Git | hunk | `git/config` 默认 pager |
| Pi | Node、zmx | Pi 运行时以及 `fish/functions/pi.fish` 的交互包装 |
| SSH / age | age、age-plugin-se | age 文档和 SSH 显式加解密任务 |
| rbw | rbw、pinentry-mac | 用户确认的密码管理基础工具；不读取本机密码库配置 |
| 发布检查 | jj、gitleaks | `scripts/check-secrets.py` |

sops、mise、gh、pinentry-mac、zoxide、Node、Go、uv 等已确认的基础工具均保留独立安装入口。

本机 `/opt/homebrew/bin/kitten` 已验证可执行。`jq` 在本机由 `/usr/bin/jq` 提供，不能误报为命令缺失；Kitty 的 Brewfile 仍显式声明 jq，以保证安装可复现。新增的安装声明本轮**未执行**。

## 功能依赖与尚缺命令

| 应用 / 功能 | 依赖 | 处理 |
|---|---|---|
| Fish 列表、搜索、系统信息、视频处理、格式化、下载与 Android 工具 | eza、fd、fastfetch、ffmpeg、prettier、tailscale、yt-dlp、android-platform-tools | 已写 `fish/Brewfile`，随显式 Fish 安装任务安装 |
| Git difftastic aliases | difftastic（命令 `difft`） | 已写 `git/Brewfile`；本机未找到 difft |
| Neovim 特定文件类型格式化 | taplo、prettier、caddy、joker | 已写 `nvim/Brewfile`；本机未找到 caddy，joker 是可选后备 |
| mise `name` 任务 | yq | 已写 `mise/Brewfile`；本机未找到 yq |
| Fish `fmd` | autocorrect | `fish/functions/fmd.fish` 引用；本机未找到，安装来源与是否保留功能待决定，未新增自动安装 |
| Goku 显示器切换 | m1ddc | `goku/karabiner.edn` 引用；本机未找到，是否使用该硬件功能待决定 |
| 发布检查 | Homebrew gitleaks | Brewfile 已声明；本机只有 mise shim，没有 Homebrew formula。检查会明确失败，不下载 |

条件 PATH、缩写和命令存在检测本身不意味着必须安装其指向的应用。Fish 中 Claude、Julia、Codex、Gemini、OpenClaw/Docker/OrbStack 等入口未自动变成安装要求；未检查外部服务仓库或认证状态。

## 配置冲突与缺文件：需要用户决定

1. **Yazi 语法主题缺文件**：`yazi/theme.toml:22` 引用 `~/.config/yazi/Catppuccin-latte.tmTheme`，仓库与当前部署目录未找到该文件。需要决定引入正确主题还是删除该引用；未擅自下载。
2. **全局 mise 的可选开发工具**：`mise/config.toml` 仍声明 Bun 及四个 npm 工具的版本选择。它们不再随任务自动安装；是否保留各工具由用户决定，未擅自卸载。

## 不是 Homebrew 安装遗漏

- Neovim Mason 管理的 LSP、shfmt、stylua、ruff、yamlfmt、kdlfmt、cljfmt；需要系统构建工具的插件另受 Xcode Command Line Tools 前提约束。
- Zellij 的 zjstatus wasm 使用配置里的固定 GitHub Release URL，由 Zellij 加载和缓存。
- Hammerspoon 的 SpoonInstall、Neovim 的 Lazy/Mason、Pi 插件可能在各自显式操作或应用启动时下载代码。这些行为不受 mise 禁自动安装设置约束，不应视为天然安全。
- macOS 提供的 pbcopy、pbpaste、osascript 等系统命令。
- 不纳管某程序的私有配置，不代表不安装该程序，例如 gh。
- 本机安装但没有仓库使用证据的软件不自动纳管，也不自动卸载。

## 已验证与未执行

已运行原生 `mise tasks validate`、按应用任务 dry-run、Kitty/Git/Bat 的真实部署预览，以及不读取私密内容的安装清单和命令路径检查。部署预览不再触发 Bat 缓存、软件安装或其他应用 setup；所有安装元数据均被排除于 symlink-each 部署。

没有运行安装、实际部署、插件更新、服务重载、SSH 解密或 Jupyter 启动。未验证新机器端到端初始化，未验证外部服务、硬件切换和所有应用运行时功能。

原生任务分散加载依据：[mise task_config](https://mise.jdx.dev/configuration/reference/task_config.md)。系统包不使用 [mise 自行实现的 Homebrew 后端](https://mise.jdx.dev/bootstrap/packages/brew.html)。
