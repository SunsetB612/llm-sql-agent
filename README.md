# 🦉 Natural-Language SQL Query System

利用 **Large Language Model (LLM)** + **Model Context Protocol (MCP)**，让你用普通话就能查 MySQL！

> 课程：数据库实践 | 期末项目

### ✅ 功能对照表

| 分类 | 已实现特性 |
|------|-----------|
| **基础任务** | - **MCP Server 运行**：基于 `alexcc4/mcp-mysql-server` 对接 MySQL<br>- **LLM→SQL 转换**：调用通义千问 API 生成查询语句<br>- **查询控制模块**：执行 SQL、返回 JSON 结果<br>- **CLI 终端界面**：自然语言交互，支持分页 `next` |
| **MCP 功能增强** | - **查询日志 `/logs`**：记录每次 SQL 与时间戳<br>- **结果分页**：大结果集分页，CLI 输入 `next` 翻页 |
| **安全控制** | - **只读白名单**：仅允许 `SELECT / SHOW / DESCRIBE …`<br>- **敏感字段拦截**：拒绝含 `password`、`salary` 等列的查询 |
| **大模型优化 / UI 扩展** | - **Few-shot Prompt 注入**：示例问答提升 SQL 生成准确率 |
