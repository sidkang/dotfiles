# Nebula（glacier）

`glacier.yml` 通过 `mise nebula:apply` 链接到 Homebrew 默认配置目录。证书组为 `sids`，仅允许 `infra` 入站；与 sentry 优先 LAN、外网 IPv4 直连，不使用 Relay。

节点私钥与证书仅存于 `/opt/homebrew/etc/nebula/host.key`、`host.crt`，不入库；`ca.crt` 从 infra 公开 CA 复制。签发由 infra 的 `mise nebula:sign glacier` 完成，导入其 `.generated/nebula/glacier.crt`。

证书就绪后先运行 `nebula -test -config /opt/homebrew/etc/nebula/`，再用 `sudo brew services start nebula` 注册系统级开机启动；停止并取消自启用 `sudo brew services stop nebula`。不另设 launchd 文件或配置同步服务。

Surge 排除 `10.8.0.0/16` 的 VIF 接管，并使 sentry 的 LAN / 公网 UDP 走 DIRECT。sentry 入口使用显式公网 IPv4，WAN 地址变化时手动更新 `glacier.yml`。
