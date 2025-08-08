# Letta Agent 模板

*本临时README由AI自动生成*

这是作者使用的 Letta agent 模板，用于 Neuro Simulator 项目。

## Letta Cloud

将 `neuro-sama.af` 上传到 Letta Cloud 后会自动生成两个 Agent：
- 一个是标准的 `memgpt_agent`
- 另一个是 `sleeptime_agent`

请手动执行以下操作：
1. 将 `sleeptime_agent` 的 System instructions 覆盖为 `sys_prompt_for_sleeptime.txt` 中的内容
2. 删除 `sleeptime_agent` 中的 `memory_persona` block（该部分内容已包含在 System instructions 中）

## 自托管 Letta Server

目前存在一些限制：
- 似乎不能直接导入 Letta Cloud 创建的模板
- 即使是从一个自托管 Letta Server 导出的带有 Sleeptime 功能的 Agent，再次导入后似乎无法创建对应的 sleeptime_agent，进而导致记忆管理功能缺失

对于普通的 Agent 导入应该可以正常工作，但作者目前没有创建示例:(

有一个较为麻烦的替代方法：
1. 先将模板导入到 Letta Cloud 中
2. 手动在自托管 Letta Server 上创建 Agent（这时候带不带 Sleeptime 功能都可以）
3. 将各个 System instructions 和 Core memory blocks 复制过去
