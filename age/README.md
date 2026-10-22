# age 加密文件

通用实现放在 `scripts/age-file.py`，不绑定 SSH，也不生成或同步 identity。

## 接收者

`recipients.txt` 只保存公开 recipient，每行一个，可用注释标明机器或恢复用途。首次加密前，先加入所有需要解密的机器和恢复 recipient。

任一接收者的 identity 均可独立解密；公开 recipient 不能解密。插件型 identity 还依赖对应插件和硬件。

本机使用 SOPS Secure Enclave identity，公开 recipient 通过以下命令派生（不能用 `age-keygen -y`）：

```sh
age-plugin-se recipients -i ~/.config/sops/age/keys.txt
```

SE identity 绑定生成它的 Mac，复制文件不能迁移解密能力。其他机器只提供公开 recipient，不传私钥。

## 使用

```sh
python3 scripts/age-file.py save \
  --file ~/.config/example/config \
  --encrypted example/config.age
```

把 `save` 换为 `check` 或 `restore` 即可比较或恢复。`--file` 是明文源文件或恢复目标，`--encrypted` 是密文路径；密文父目录需预先存在。

默认读取共享 `age/recipients.txt`；identity 使用 `SOPS_AGE_KEY_FILE`，未设置时为 `~/.config/sops/age/keys.txt`。也可以显式指定 `--recipients PATH` 和 `--identity PATH`。identity 必须在仓库外，权限为 `0600` 或更严格。插件解密可能需要 Touch ID 或终端交互。

`save` 只在内容变化时重写密文，且写入前进行解密回验；本机 identity 必须能够解开新的密文。失败时不替换已有密文。`check` 只读比较内容，不验证接收者列表是否更新。不会输出明文或把明文写入仓库。

## 更新接收者

修改列表后，对每个受影响的密文显式重新加密，即使明文没有变化：

```sh
mise ssh:save -- --reencrypt
```

普通 `save` 会跳过内容未变的文件，不自动应用接收者变更。新增接收者只能解开重新加密后的版本；旧版本不会改变。移除接收者也不能撤销其对旧版本的解密能力。

每台目标机器应分别运行 `check` 验证自己的 identity；单台机器回验成功不代表所有目标机器都已验证。

## 恢复保护

`restore` 不覆盖不同的现有文件，不替换软链接；相同文件不改动。新文件以 `0600` 原子安装，父目录要求为 `0700` 或更严格，不存在时会创建。明文恢复临时文件只在目标目录中创建，权限为 `0600`，结束后删除。

