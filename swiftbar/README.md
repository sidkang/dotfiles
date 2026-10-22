# SwiftBar

插件目录：`~/.config/swiftbar`，由根 `mise.toml` 逐文件链接。

```sh
mise run --dry-run swiftbar:install
mise swiftbar:plan
# 仅在缺少依赖时显式安装：mise swiftbar:install
mise swiftbar:apply
mise swiftbar:setup
mise swiftbar:restart  # 切换目录后重启；日常刷新用 swiftbar:reload
mise swiftbar:test
```

安装、部署、设置目录及刷新均独立，不自动串联。插件只用 Python 标准库，
直接使用 Homebrew Python 3.14，不再使用旧 mise 虚拟环境。

`token-usage.10m.py` 每十分钟刷新；`swiftbar_menu.py` 是辅助模块，
由 `.swiftbarignore` 排除。测试和安装元数据不部署。

Pi 会话默认取 `~/.config/pi/agent/sessions`，支持 `PI_CODING_AGENT_DIR`
和优先级更高的 `PI_USAGE_SESSIONS_DIR`。OpenCode 的数据库和同步目录仍沿用
脚本原有默认值及环境变量覆盖；不部署、不收录任何会话、数据库或统计快照。

旧目录的 `secrets.py` 和 `pbcopy` 只在本机保留于 `~/.config/swiftbar/`，
不读取、不纳管，也不作为插件运行。
