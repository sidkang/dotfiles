# Nebula CA（操作员）

`ca.crt` 与 `ca.key.age` 通过 `mise nebula:apply` 链接到 `~/.config/nebula/`，供 infra 的 `mise nebula:sign` 签发节点证书使用。

glacier 本机 Nebula 运行配置位于 infra 的 `inventory/nebula/glacier.yml`，直接写入 `/opt/homebrew/etc/nebula/config.yml`，不由 dotfiles 链接。
