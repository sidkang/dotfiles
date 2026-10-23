# gitleaks

安装依赖声明在 `scripts/Brewfile`；先审查该文件，再显式运行 `mise scripts:install`。使用内置检测规则，无配置文件需要部署。

发布前检查待发布文件树和提交历史。使用 `--redact` 隐藏检测结果中的密钥；不要扫描包含未跟踪私密文件的整个工作目录。

根 `.gitleaksignore` 只按指纹忽略已核实的历史误报：4 个旧提交中的 ResponsesClient 模拟请求脱敏测试，共 8 条。每条限定提交、文件、规则和行号，不排除整个文件或未来告警。
