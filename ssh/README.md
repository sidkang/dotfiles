# SSH 配置

只保存 `~/.ssh/config` 的 age 密文 `config.age`；不收录 `Include` 引用文件、密钥、`known_hosts` 或 agent 状态。

```sh
mise ssh:save       # 修改后加密并回验；内容未变则不重写
mise ssh:check      # 只读比较；已包含在发布检查 mise check 中
mise ssh:restore    # 恢复；拒绝覆盖不同内容或软链接
```

不会在 JJ 操作或部署时隐式保存、恢复。新建恢复文件为 `0600`，新目录为 `0700`；内容相同的现有文件保持不变。

首次使用先配置[接收者和仓库外 identity](../age/README.md)。接收者变化后运行 `mise ssh:save -- --reencrypt`；仅有仓库而没有匹配 identity，无法恢复。

任务复用 `scripts/age-file.py`，可传入 `--identity PATH` 或 `--file PATH`；后者可用于隔离验证，避免改动现用配置。
