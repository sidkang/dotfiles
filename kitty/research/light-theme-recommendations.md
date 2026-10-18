# 浅色终端主题建议

## 结论

以 Latte（`#eff1f5` / `#4c4f69`）与 Dawnfox（`#faf4ed` / `#575279`）为基准，优先试 **Dayfox、Iceberg Light、Seoul256 Light**；第四备选是 **Zenwritten Light**。它们来自 [Terminal Colors 的 light 标签页](https://terminalcolors.com/tags/light/)，共同避免纯白底和黄褐纸张感；排序偏向柔和底色、灰蓝/紫灰文字与低噪声。

1. **[Dayfox](https://terminalcolors.com/themes/nightfox/dayfox/)** — `#f6f2ee` / `#3d2b5a`，最接近 Dawnfox：同为柔暖的非纯白底，但文字转为深紫灰；主色是低亮度蓝 `#2848a9`、青 `#287980`、紫 `#6e33ce`，红绿黄也较收敛。相对 Latte 的冷灰底更暖、相对 Dawnfox 对比更强；若不喜欢奶油/棕调或命令输出中的紫色存在感，排到 Iceberg 后。
2. **[Iceberg Light](https://terminalcolors.com/themes/iceberg/light/)** — `#e8e9ec` / `#33374c`，最像 Latte 的冷调灰紫阅读面，且背景更沉静、文字为 slate 蓝灰。蓝/紫/青为 `#2d539e` / `#7759b4` / `#3f83a6`，红绿黄为柔和的 `#cc517a` / `#668e3d` / `#c57339`；比 Latte 更低饱和、更少跳色。代价是字色更深、总体比 Dawnfox 更冷且阅读对比略高。
3. **[Seoul256 Light](https://terminalcolors.com/themes/seoul256/light/)** — `#dadada` / `#4e4e4e`，较深的中性灰底和灰字，视觉最安静；仅以压低饱和度的蓝 `#5f87ae`、紫 `#875f87`、青 `#5f8787` 点缀。比 Latte/Dawnfox 暗一档、前景也不带蓝紫，适合想减少 UI 存在感；代价是色彩辨识与层次较弱。
4. **[Zenwritten Light](https://terminalcolors.com/themes/zenbones/zenwritten-light/)** — `#eeeeee` / `#353535`，接近 Latte 的柔灰底、但前景中性。蓝 `#286486`、紫 `#88507d`、青 `#3b8992` 都克制，适合低噪声。代价是棕黄 `#944927`、橄榄绿 `#4f6c31` 使其比前三者更偏纸感，故仅作备选。

## 明确排除

不选既已不适的 Gruvbox/Everforest/Rosé Pine Dawn/Noctis Lux/Tomorrow Default；也排除同类模式：Kanagawa Lotus、Solarized Light（黄褐/sepia），Tomorrow Default、One/One Half、GitHub Light、Ayu、Night Owl Light（纯白或近纯白），Tokyo Night Day 与 Ayu（亮蓝、洋红或红色过电、饱和度偏高）。因此没有把 Tokyo Night Day 虽然是冷灰底的方案列入。

## 取色依据

上述背景、前景与 ANSI 主色均直接取自 Terminal Colors 的 Ghostty 导出：[Dayfox](https://terminalcolors.com/downloads/ghostty/nightfox-dayfox)、[Iceberg Light](https://terminalcolors.com/downloads/ghostty/iceberg-light)、[Seoul256 Light](https://terminalcolors.com/downloads/ghostty/seoul256-light)、[Zenwritten Light](https://terminalcolors.com/downloads/ghostty/zenbones-zenwritten-light)；参照值来自 [Latte](https://terminalcolors.com/downloads/ghostty/catppuccin-latte) 与 [Dawnfox](https://terminalcolors.com/downloads/ghostty/nightfox-dawnfox)。
