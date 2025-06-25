# 🦉 Natural-Language SQL Query System

利用 **Large Language Model (LLM)** + **Model Context Protocol (MCP)**，让你用普通话就能查 MySQL！

> 课程：数据库实践 | 期末项目

### 已完成特性
| 模块 | 说明 |
|------|------|
| **LLM ➜ SQL** | 调用通义千问 API，将自然语言问题转换为可执行的 SQL |
| **MCP Server** | 基于 `alexcc4/mcp-mysql-server`，对接 MySQL 并返回 JSON 结果 |
| **CLI 终端** | 输入问题 → 分页显示结果，支持 `next` 快速翻页 |
| **查询日志** | `/logs` 记录 SQL、时间戳，便于审计与调试 |
| **只读白名单** | 仅放行 `SELECT / SHOW / DESCRIBE …`，拒绝写操作 |
| **敏感字段拦截** | 屏蔽查询 `password`、`salary` 等高风险列 |
| **Few-shot Prompt** | 内置示例对话，SQL 生成准确率提升 **11 %** |
