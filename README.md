# 🦉 Natural-Language SQL Query System


## 📋 项目概述

利用 **Large Language Model (LLM)** + **Model Context Protocol (MCP)**，让你用普通话就能查询 MySQL！
本项目是一个创新的数据库查询系统，允许用户使用自然语言查询数据库，无需编写复杂 SQL 语句。

### ✨ 核心特性

- 🤖 **智能 SQL 生成**：基于通义千问 API，将自然语言转换为准确 SQL 查询  
- 🔒 **多重安全防护**：只读权限控制、敏感字段保护、SQL 注入防御  
- 📊 **多界面支持**：命令行界面(CLI) + 图形界面(GUI)  
- 📝 **完整日志系统**：查询历史和执行时间追踪  
- 🔍 **智能分页**：大结果集自动分页显示  

## 🚀 快速开始

### 1. 环境准备
```bash
conda create -n llm-mcp python=3.10
conda activate llm-mcp
```

### 2. 安装项目
```bash
git clone https://github.com/SunsetB612/llm-sql-agent.git
cd llm-sql-agent
pip install -r requirements.txt
```

### 3. 配置环境
将 `.env.example` 重命名为 `.env` 并填写配置：
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

### 4. 启动服务

**步骤1：启动后端服务**
```bash
python src/mcp_http_server.py
```

**步骤2：启动前端服务**

1. 图形界面：
```bash
streamlit run src/mcp_streamlit.py
```

2. 命令行界面：
```bash
python src/mcp_cli.py
```

## 🎯 使用示例

输入自然语言查询：
- "显示所有用户信息"
- "查找年龄大于25的用户"  
- "统计每个部门的员工数量"
- "查找销售额最高的前10个产品"
