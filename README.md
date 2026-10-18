# dotfiles

jj（与 Git 共存）管版本，`mise dot` 管部署，`mise bootstrap` 管软件安装和初始化。
每个顶层目录是一个程序的配置，映射全部写在 `mise.toml`。

多数程序是简单映射，不在此列出。需要注意的：

| 程序 | 目标 | 说明 |
| --- | --- | --- |
| Bat | `~/.config/bat/` | 改主题后运行 `bat cache --build` |
| btop | `~/.config/btop/` | btop 会改写 `btop.conf`，改动直接进仓库 |
| Espanso | `~/Library/Application Support/espanso/{config,match,script}` | 整目录链接 |
| Fish | `~/.config/fish/` | 独立命令在 `functions/<name>.fish`（不用 `funcsave`），按功能分组的在 `conf.d/<功能>.fish`；密钥在 Git 忽略的 `conf.d/secrets.fish` |
| pi | `~/.config/pi/agent/` | 需要 fish 设置的 `PI_CODING_AGENT_DIR`。只链接配置（`subagent-manager/` 例外：插件拒绝软链接，改为复制；插件自己改动后用 `mise dot add ~/.config/pi/agent/subagent-manager` 收回仓库）；`auth.json`、`sessions/`、`npm/`、`git/` 和缓存留在本机。扩展和 skills 来自 git 包 `github.com/sidkang/pi-stuff`，由 `bootstrap` 任务的 `pi update --extensions` 安装。`sessions/` 由 Syncthing 原地同步，不进 Git |
| mise | `~/.config/mise/{config.toml,tasks}` | 全局配置与任务；本机覆盖写在不进仓库的 `config.local.toml` |
| Zellij | `~/.config/zellij/` | zjstatus 插件从固定版本的 GitHub release URL 加载，不提交 wasm |
| Git | `~/.config/git/` | 不使用 `~/.gitconfig` |

新增程序：建 `<程序>/` 目录，在 `[dotfiles]` 加一行，在 `[bootstrap.packages]` 声明软件。

私有文件被 Git 忽略，不会发布：`fish/conf.d/secrets.fish`、`pi/agent/models.json`、`espanso/match/mine.yml`、`espanso/match/packages/`。

## 新机器

需要 Git、Homebrew 和 mise 2026.10.13 或更新版本，仅支持 macOS。

```sh
git clone https://github.com/sidkang/dotfiles.git ~/config/dotfiles
cd ~/config/dotfiles
mise trust                 # 先审查 mise.toml
mise bootstrap --only packages,dotfiles,task --dry-run
mise bootstrap --only packages,dotfiles,task
mise dot status
```

bootstrap 安装缺少的软件（不升级已有的），建立链接，再运行 `bootstrap` 任务：
从 AeroSpace 的 tap 安装它（mise 无法声明这个 tap），并构建 Bat 缓存。
目标位置已有文件时会停下；先备份，不要默认加 `--force`。

## 日常修改

直接编辑本目录的文件，已链接的配置立即生效。新增、删除文件或修改映射后：

```sh
mise dot diff
mise dot apply --dry-run
mise dot apply
```

在其他目录可用 `mise -C ~/config/dotfiles dot apply`。
解除部署用 `mise dot unapply`；它不会恢复部署前的文件。

## 发布

```sh
jj status
jj diff
mise exec gitleaks@8.30.1 -- gitleaks dir . --redact
mise exec gitleaks@8.30.1 -- gitleaks git . --redact
jj commit -m "feat(<程序>): ..."
jj bookmark move master --to @-
jj git push
```

jj 会自动纳入所有未被忽略的新文件。私有文件要先写进 `.gitignore`，再运行任何 jj 命令。
仓库是公开的：秘密放密码管理器或 Git 忽略的本地文件。已泄露的凭据要轮换，删文件不够。

## 获取更新

`jj git fetch` 不改动工作区。rebase 之后已链接的配置会立即改变，所以先审查：

```sh
jj git fetch
jj log -r '@-..master'
jj diff --from @- --to master
jj rebase -d master
mise dot apply --dry-run
mise dot apply
```

## 第三方内容

`bat/themes/Catppuccin Latte.tmTheme` 来自 https://github.com/catppuccin/bat ，Copyright (c) 2021 Catppuccin，MIT License。
