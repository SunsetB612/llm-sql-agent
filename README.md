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

---

## 🚀 快速开始（运行说明）

### 1. 安装依赖

建议使用 Python 3.12+，并提前创建虚拟环境。

```bash
pip install -r requirements.txt
# 或者直接安装主要依赖
pip install streamlit flask mysqlclient python-dotenv
```

### 2. 配置环境变量

在项目根目录下新建 `.env` 文件，内容如下（请根据实际数据库和API信息填写）：

```ini
# MySQL 数据库连接
DB_HOST=localhost
DB_PORT=3306
DB_USER=你的数据库用户名
DB_PASSWORD=你的数据库密码
DB_NAME=你的数据库名

# 通义千问 API Key
DASHSCOPE_API_KEY=你的DashScope API Key
```

### 3. 启动后端 MCP-MySQL-Server（HTTP API）

```bash
python src/mcp_server.py
```

默认会在 `0.0.0.0:8000` 启动 HTTP API 服务。

### 4. 启动可视化前端（Streamlit）

```bash
streamlit run src/mcp_streamlit.py
```

启动后访问命令行输出的本地地址（如 http://localhost:8501 ），即可使用自然语言查询和可视化。

---

如需命令行体验，可运行：

```bash
python src/mcp_cli.py
```

---
