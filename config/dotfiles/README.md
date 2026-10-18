# Bat / Starship：mise 历史与 bootstrap

直接编辑本机实际配置，由 mise 保存版本；不再从源码 checkout 建立链接。
远端约定：`https://github.com/sidkang/dotfiles.git`，分支 `master`。
采用手动保存、手动同步，不安装后台 watcher。

## 文件范围

- `~/.config/bat/`：配置、四种 Catppuccin 主题及许可证。
- `~/.config/starship.toml`：提示符配置。
- `~/.config/mise/conf.d/dotfiles.toml`：共享的追踪声明与 bootstrap 配置。
- `~/.config/mise/dotfiles/`：本说明与维护规则。

现有 `~/.config/mise/config.toml` 和其他全局配置不在本次共享范围内。
不要递归追踪整个 `~/.config/mise`，其中可能有解密私钥、本机配置和其他秘密。

## 日常修改与保存

```sh
# 直接编辑 ~/.config/bat/config 或 ~/.config/starship.toml
mise -C ~ dot history diff
mise -C ~ dot save -d "调整提示符或主题"
mise -C ~ dot history
```

修改 Bat 主题后运行 `bat cache --build`。保存历史不会发布到 GitHub。
`mise dot status` 没有 watcher 是预期情况，不要按其建议自动启用服务。

## 首次发布：需要明确批准

连接前检查 `mise -C ~ dot paths` 与全部已保存历史，并扫描秘密：

```sh
# 默认状态目录下的 bare history；若修改了 MISE_STATE_DIR，请使用对应路径。
mise -C ~ exec gitleaks@8.30.1 -- gitleaks git ~/.local/state/mise/history/repo.git --redact
```

扫描不能代替人工审查。public 仓库不能发布明文秘密。
`origin set` 会立即执行首次同步，`--sync manual` 并不阻止这一次发布。
批准发布后才执行：

```sh
mise -C ~ dot origin set https://github.com/sidkang/dotfiles.git --branch master --sync manual
```

首次发布后确认 GitHub 默认分支为 `master`。不要用普通 Git push 发布旧 checkout。
连接之后，`mise -C ~ dot sync` 会发布全部待同步 checkpoint 并获取远端更新。

## 当前机器初始化

```sh
mise -C ~ bootstrap --only packages,dotfiles,task --dry-run
mise -C ~ bootstrap --only packages,dotfiles,task
```

只确保 macOS 上的 Bat、Starship 软件存在，并构建 Bat 主题缓存。
不安装第二份 mise `[tools]` 版本，不改变 Fish 初始化或启动 watcher。
包声明默认接受当前已安装版本，不会每次运行都升级。

## 其他机器：发布后使用

先安装 Git 和支持本配置的 mise（已验证 2026.10.13）。若以后加入加密文件，
先从独立备份取得 age 私钥，不要依赖加密历史来提供自己的解密密钥。

先检查远端内容，再预览与恢复：

```sh
env MISE_HISTORY_SYNC=manual mise -C ~ bootstrap --adopt 'https://github.com/sidkang/dotfiles.git?ref=master' --only packages,dotfiles,task --dry-run
env MISE_HISTORY_SYNC=manual mise -C ~ bootstrap --adopt 'https://github.com/sidkang/dotfiles.git?ref=master' --only packages,dotfiles,task
mise -C ~ dot status
```

环境变量确保恢复配置之前也采用手动模式；恢复出的共享模块同样设置为 manual。
已有不同文件时先处理冲突，不默认使用 `--take-remote-all` 或 `--replace-history`。
旧的主配置没有被共享是有意的；首次连接时未追踪它的提示不代表需要加入它。
该包声明面向 macOS，其他平台需自行提供 Bat、Starship 或增加对应包声明。

## 日常接收更新

```sh
mise -C ~ dot sync
mise -C ~ dot pull
```

`sync` 发布并获取，`pull` 才写入实际文件；它们不会自动执行 bootstrap。
包声明或初始化任务改变后，再运行上面的受限 bootstrap。普通 Bat 主题更新后，
运行 `bat cache --build` 即可。

## 回退

```sh
mise -C ~ dot history --path ~/.config/starship.toml
mise -C ~ dot rollback ~/.config/starship.toml
# 撤销刚才的回退
mise -C ~ dot undo
```

先阅读命令给出的预览再确认。回退会保存新的历史，不会抹掉旧秘密，
也不能撤销所有软件安装或系统操作。

## 第三方主题

Catppuccin 主题来自旧配置，原样保留；精确上游 revision 未记录。
上游：https://github.com/catppuccin/bat

Copyright (c) 2021 Catppuccin，MIT License。许可证随主题配置保存在
`~/.config/bat/LICENSE.catppuccin`。
