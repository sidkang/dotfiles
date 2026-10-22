# dotfiles

jj 管版本，`mise dot` 管部署，`mise bootstrap` 管软件安装和初始化。软件、部署映射及 bootstrap 任务统一写在根目录 `mise.toml`。

需要注意的配置：

- **Bat**：修改主题后运行 `bat cache --build`。
- **btop**：运行时会回写 `btop.conf`，改动直接进入仓库。
- **Hammerspoon**：bootstrap 设置 `MJConfigFile` 指向 `~/.config/hammerspoon/init.lua`；更改入口后需重启应用。
- **pi**：依赖 fish 设置的 `PI_CODING_AGENT_DIR`。只链接配置，认证、会话和缓存留在本机；会话由 Syncthing 同步。`subagent-manager/` 采用复制，插件修改后用 `mise dot add ~/.config/pi/agent/subagent-manager` 收回仓库。
- **本机文件**：mise 覆盖配置写到 `~/.config/mise/config.local.toml`，Fish 密钥只放 `fish/conf.d/secrets.fish`；其他私有文件见 `.gitignore`。
- **tmux**：`tmux/` 只归档，不安装或部署。

配置纳管与排除偏好见 [CONFIG-POLICY.md](CONFIG-POLICY.md)；检查遗漏前先看该文件，避免重复建议已决定不纳管的程序。

新增程序：建 `<程序>/`，在 `mise.toml` 的 `[dotfiles]` 添加映射，在 `[bootstrap.packages]` 声明软件。

## 新机器

支持 macOS，需 Git、Homebrew 和 mise（最低版本见 `mise.toml` 的 `min_version`）。

```sh
brew install jj
jj git clone https://github.com/sidkang/dotfiles.git ~/config/dotfiles
cd ~/config/dotfiles
mise trust                 # 先审查 mise.toml
mise bootstrap --only packages,dotfiles,task --dry-run
mise bootstrap --only packages,dotfiles,task
mise dot status
```

遇到目标文件冲突时先备份处理，不要直接加 `--force`。

## 日常修改

编辑已链接的源文件会直接影响本机配置。新增、删除文件或修改映射后：

```sh
mise dot diff
mise dot apply --dry-run
mise dot apply
```

解除部署用 `mise dot unapply`，不会恢复部署前的文件。

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

私有文件先加入 `.gitignore`，再运行 jj。凭据泄露后需轮换，仅删文件不够。

## 获取更新

rebase 会影响已链接的配置，先审查差异：

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
