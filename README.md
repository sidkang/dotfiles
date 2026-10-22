# dotfiles

jj 管版本，`mise dot` 管部署。根 `mise.toml` 保存部署映射；各应用的安装要求和操作放在自己的目录。

## 按应用操作

支持 macOS，需 Git、Homebrew 和 mise（最低版本见 `mise.toml`）。新机器先通过 Homebrew 安装 `git`、`jj`、`mise`，克隆后审查配置并运行 `mise trust`。

每个应用包含：

- `Brewfile`：该应用的安装依赖，共享依赖由各使用方重复声明，Homebrew 去重。
- `tasks.toml`：该应用独立的安装、部署和维护任务。

以 Kitty 为例：

```sh
# 先看依赖，再看命令与实际部署差异；这些步骤都不安装。
less kitty/Brewfile
mise run --dry-run kitty:install
mise kitty:plan

# 按需要分别执行，没有自动串联。
mise kitty:install
mise kitty:apply

# 服务操作另外选择；apply 不启动、不重启。
mise kitty:start
mise kitty:reload          # 要求确认，会重启后台实例
```

其他应用使用相同的 `<app>:install`、`<app>:plan`、`<app>:apply` 命名。只有软件、没有部署映射的目录仅提供安装任务。`mise tasks` 查看全部任务。

**不要为了单个配置运行全量 bootstrap 或通配符安装任务。** 没有全局包安装 hook，也没有通用 bootstrap 初始化任务。`mise dot apply` 不带目标仍会部署全部映射，日常优先用应用的 `:plan` / `:apply`。

系统包只调用真正的 `brew bundle install --no-upgrade`。缺少 Homebrew、安装失败或 tap 未获信任时停止，不使用 mise 的 Homebrew 后端，不自动信任 tap，不切换安装器。任务执行、`mise exec` 和命令缺失均禁止自动安装工具。显式运行 `mise install` 仍是安装行为，不属于检查。

每个应用只维护一份 `Brewfile`，包含该配置所用的安装依赖，不再区分默认和 extras。`:install` 会安装该文件里的全部项目，执行前先审查；只补某一项时可直接用 `brew install <package>`。

## 配置与维护

多数配置是软链接，编辑源文件会立即影响本机。新增文件或改映射后，先运行对应应用的 `:plan`，再选择 `:apply`。遇到目标冲突先处理，不加 `--force`。

下列操作与部署分开，必须显式执行：

| 任务 | 副作用 |
|---|---|
| `mise bat:cache` | 重建 Bat 缓存 |
| `mise hammerspoon:setup` | 修改 Hammerspoon 的 `MJConfigFile` 偏好 |
| `mise kitty:start` | 后台服务未运行时启动 Kitty |
| `mise kitty:reload` | 重启 Kitty 后台实例，要求确认 |
| `mise pi:extensions` | 更新 Pi 扩展，可能执行 npm 生命周期脚本，要求确认 |

安装任务本身也可能执行 Homebrew formula/cask 的安装脚本；应用首次启动还可能由 Lazy、Mason、SpoonInstall 等下载插件。任务拆分不代表这些操作天然安全。

- 新增程序：建 `<app>/Brewfile` 和 `<app>/tasks.toml`；有配置部署时在根 `[dotfiles]` 增加映射。不要把安装元数据部署到应用配置目录。
- Node、Go、uv 默认由 Homebrew 提供；mise 只保留需要时由项目显式选择的旧版 Node。其他现有 mise 工具选择见 `mise/config.toml`，不随任务自动安装。
- **IPython**：Fish 设置 `IPYTHONDIR=~/.config/ipython`；只部署默认 profile 的配置，历史数据库和其他运行状态留在本机。启动时尝试加载 `icecream.ic`，未安装则跳过。
- pi 的 `subagent-manager/` 使用复制；本机修改后用 `mise dot add ~/.config/pi/agent/subagent-manager` 收回仓库。部署前检查，不自动覆盖。
- SSH 只保存 age 密文，恢复、保存、检查都是[显式操作](ssh/README.md)，不随部署执行。
- `mise dot unapply` 不会恢复部署前的文件。

依赖审计及待决定项见 [DEPENDENCIES.md](DEPENDENCIES.md)。纳管例外和私有数据边界见 [CONFIG-POLICY.md](CONFIG-POLICY.md)。

## 发布

```sh
jj status
jj diff
# 若缺少检查依赖，先审查 scripts/Brewfile，再显式 mise scripts:install。
mise check                 # 任务校验、SSH 密文比对、工作树及历史泄密扫描
jj commit -m "feat(<程序>): ..."
jj bookmark move master --to @-
jj git push
```

私有文件先加入 `.gitignore`，再运行 jj。SSH 配置修改后先运行 `mise ssh:save`；`check` 不自动保存，可能要求 Touch ID。泄密检查直接使用已有 `gitleaks`，不自动安装。

## 获取更新

rebase 会影响已链接的配置，先审查差异并确认，再执行变基：

```sh
jj git fetch
jj log -r '@-..master'
jj diff --from @- --to master
# 确认后才执行 jj rebase -d master
# 根据实际变更选择相应 <app>:plan / :install / :apply。
```

## 第三方内容

`bat/themes/Catppuccin Latte.tmTheme` 来自 https://github.com/catppuccin/bat ，Copyright (c) 2021 Catppuccin，MIT License。
