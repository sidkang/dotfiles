## Engineering Defaults

- Choose the simplest implementation that fully satisfies requirements and preserves contracts.
- Design deep modules.
- Introduce an abstraction only when it simplifies the current implementation, removes demonstrated duplication, or represents a current domain boundary.
- If `.jj/` exists, use `jj` rather than `git` for version-control operations.

## Subagents

- Agent types set default thinking levels. For very hard tasks, raise the level with a `:thinking` suffix on the `agent_spawn` model, e.g. `claude/opus-5.5:high`.

## Documentation Defaults

- 文档默认极简，只保留使用必需的信息和项目特有的配置。
- 通用操作直接链接上游或官方文档，不复写教程，不堆砌提醒、背景或重复说明；用户明确要求时再展开。
- 修改文档时优先删减，不因一次排错把过程和临时注意事项写进长期文档。
