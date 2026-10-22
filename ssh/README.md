# SSH 配置

只保存 `~/.ssh/config` 的 age 密文 `config.age`。SSH 私钥、公钥、`known_hosts` 和 agent 状态均不读取、不纳管；`Include` 引用的其他配置不会自动收录。

```sh
mise ssh:save       # 加密并回验；内容未变则不重写
mise ssh:check      # 只读比较，内容不同则失败
mise ssh:restore    # 恢复；拒绝覆盖不同的现有配置
```

实现复用 `scripts/age-file.py`。共享接收者、现有 SOPS identity、SE 硬件限制和接收者变更操作见 [age/README.md](../age/README.md)。不创建新密钥，不在普通 JJ 操作或 `mise dot apply` 时隐式保存或恢复。

修改现用配置后运行 `save`，发布前运行 `check`。首次保存前，应先补齐 `age/recipients.txt` 中所有目标机器及恢复用途的公开 recipient。不能仅凭仓库在没有匹配 identity 的机器上恢复。

默认 identity 为 `~/.config/sops/age/keys.txt`，可通过 `SOPS_AGE_KEY_FILE` 或任务参数 `--identity PATH` 指定其他仓库外 identity。插件解密可能要求 Touch ID。

接收者变化后，即使配置未变也需要：

```sh
mise ssh:save -- --reencrypt
```

恢复结果为权限 `0600` 的普通文件；新目录为 `0700`。现有配置不同或目标为软链接时报错，不覆盖，不部署或修复 SSH 密钥。

可通过 `--file PATH` 指定隔离验证目标，避免改动现用配置。
