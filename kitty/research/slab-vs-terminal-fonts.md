# Slab 与终端编程字体：社区采用信号（2026-07-18）

## 结论

Slab-serif 编程字体**确实可用于终端，且不是罕见到没有实际支持**：Iosevka 官方同时发布 `Iosevka Slab`、`Iosevka Term Slab` 和 Fixed Slab。可是，现有可核验的公开信号更支持「非 slab 的开发/终端字体是主流选择」，不足以给出整个社区的市场份额或严格排名。JetBrains Mono、Fira Code、Cascadia Code/Mono 都是非 slab；其中 Cascadia 随 Windows Terminal 发布并为 Visual Studio 默认字体。

关键不要混同两个维度：**slab/无衬线是字形外观**；`Term`/`Mono`/`Fixed` 常是宽度、连字或终端兼容语义。Iosevka 的 `term` 会缩窄箭头和几何符号以适配终端，而 `slab` 只把字形转为 slab-serif；两者可组合成 Term Slab。Sarasa 亦将 Mono/Term/Fixed 以破折号宽度和连字差异区分，且其字库基于 Inter、Iosevka、Source Han Sans，并非「slab」类别。

## 可观察证据与边界

* Iosevka 最新版单一发布资产的下载数中，普通 TTC 为 872、Slab TTC 为 279、Term Slab TTF 为 88：这是同一项目同一版本下的弱偏好信号，不能把不同格式、安装方式或未列出的资产相加后当作用户数。
* 非 slab 字体的官方发布资产下载量很大（Fira Code 6.2 为 2,861,550，JetBrains Mono 2.304 为 442,464，Cascadia 2407.24 为 291,375），但版本年代、资产内容和分发渠道不同，**不可横向换算份额**。GitHub star、编辑器默认值和配置示例同样只是可见度/采用线索，不是终端字体普查。
* IBM Plex 官方确有 Plex Mono；「Roboto Slab」与「Roboto Mono」应分别核实来源，未找到可归因的官方“Roboto Slab Mono”，故不以该名称作实例。

## 实践含义

若偏好 slab，可放心试 Iosevka Term Slab；若首要目标是广泛默认集成、连字生态或常见终端配置，先比较 JetBrains Mono、Fira Code、Cascadia Mono 与 Iosevka Term。选择时单独测试终端的 box-drawing、Powerline/Nerd glyph、CJK 回退和连字，而不要由 serif/slab 外观推断宽度兼容性。

## 来源

* https://github.com/be5invis/Iosevka/blob/main/doc/PACKAGE-LIST.md
* https://github.com/be5invis/Iosevka/blob/main/doc/custom-build.md
* https://api.github.com/repos/be5invis/Iosevka/releases/latest
* https://github.com/be5invis/Sarasa-Gothic/blob/master/README.md
* https://github.com/microsoft/cascadia-code
* https://api.github.com/repos/tonsky/FiraCode/releases/latest
* https://api.github.com/repos/JetBrains/JetBrainsMono/releases/latest
* https://api.github.com/repos/microsoft/cascadia-code/releases/latest
* https://github.com/IBM/plex
