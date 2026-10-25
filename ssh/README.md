# SSH 配置

只保存 `~/.ssh/config` 的 age 密文 `config.age`；不收录 `Include` 引用文件、密钥、`known_hosts` 或 agent 状态。

```sh
mise ssh:apply      # 远端 → 本机：一次解密完成预览、确认、应用及校验；不留备份
mise ssh:save       # 本机 → 仓库：加密并回验；内容未变则不重写
mise ssh:check      # 独立只读比较；已包含在发布检查 mise check 中
mise ssh:restore    # 首次恢复；拒绝覆盖不同内容或软链接
```

`apply` 仅显示差异行号和增删数量，不输出配置内容；默认交互确认，明确授权后可加 `--yes`。`--dry-run` 只预览，但仍需一次解密。日常同步直接用 `apply`，无需前后串联 `check` / `restore` / `save`；单独再运行会重新解密。

不会在 JJ 操作或部署时隐式保存、恢复。写入文件为 `0600`，新目录为 `0700`；内容相同的现有文件保持不变。

首次使用先配置[接收者和仓库外 identity](../age/README.md)。接收者变化后运行 `mise ssh:save -- --reencrypt`；仅有仓库而没有匹配 identity，无法恢复。

任务复用 `scripts/age-file.py`，可传入 `--identity PATH` 或 `--file PATH`；后者可用于隔离验证，避免改动现用配置。
