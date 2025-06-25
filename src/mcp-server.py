from typing import Any, Dict, List
import os
import logging
import time
from pathlib import Path

import MySQLdb
import MySQLdb.cursors

from mcp.server.fastmcp import FastMCP
import dotenv

dotenv.load_dotenv()

# 创建MCP服务器实例
mcp = FastMCP("mysql-server")

# 数据库连接配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER"),
    "passwd": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306))
}

# ----- 日志功能 -----
def ensure_log_directory():
    """确保日志目录存在，目录在项目根目录下的 logs 文件夹"""
    # 项目根目录，假设当前文件在 /src 或更深目录下
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / "logs"
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
        print(f"创建日志目录: {log_dir}")
    return log_dir

def setup_logger():
    """设置日志配置，日志追加写入"""
    log_dir = ensure_log_directory()
    log_file = log_dir / f"mcp_mysql_{time.strftime('%Y%m%d')}.log"

    logger = logging.getLogger('mysql-mcp-server')
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 追加模式打开日志文件
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    print(f"日志文件路径: {log_file.resolve()}")
    return logger

logger = setup_logger()

def read_log_file(path: str, max_lines: int = 100) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    logs = []
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    lines = lines[-max_lines:]
    for line in reversed(lines):
        parts = line.strip().split(" - ")
        if len(parts) >= 4:
            timestamp = parts[0]
            logger_name = parts[1]
            level = parts[2]
            message = " - ".join(parts[3:])
            logs.append({
                "timestamp": timestamp,
                "logger": logger_name,
                "level": level,
                "message": message
            })
    return logs
# ----- 日志功能整合结束 -----


def get_connection():
    try:
        return MySQLdb.connect(**DB_CONFIG)
    except MySQLdb.Error as e:
        logger.error(f"数据库连接失败: {e}")
        raise


@mcp.resource("mysql://schema")
def get_schema() -> Dict[str, Any]:
    """提供数据库表结构信息"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [list(table.values())[0] for table in tables]

        schema = {}
        for table_name in table_names:
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            table_schema = []

            for column in columns:
                table_schema.append({
                    "name": column["Field"],
                    "type": column["Type"],
                    "null": column["Null"],
                    "key": column["Key"],
                    "default": column["Default"],
                    "extra": column["Extra"]
                })

            schema[table_name] = table_schema

        return {
            "database": DB_CONFIG["db"],
            "tables": schema
        }
    finally:
        if cursor:
            cursor.close()
        conn.close()


def is_safe_query(sql: str) -> bool:
    """基本的SQL安全检测，只允许SELECT等只读查询"""
    sql_lower = sql.strip().lower()

    safe_keywords = ['select', 'show', 'describe', 'desc', 'explain']
    dangerous_keywords = [
        'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'truncate', 'replace', 'merge', 'call', 'exec', 'execute'
    ]

    starts_with_safe = any(sql_lower.startswith(keyword) for keyword in safe_keywords)
    contains_dangerous = any(keyword in sql_lower for keyword in dangerous_keywords)

    return starts_with_safe and not contains_dangerous


@mcp.tool()
def query_data(sql: str) -> Dict[str, Any]:
    """执行只读SQL查询"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    logger.info("=== 新的SQL查询开始 ===")
    logger.info(f"时间戳: {timestamp}")
    logger.info(f"SQL语句: {sql}")

    if not is_safe_query(sql):
        logger.warning(f"不安全查询被拒绝: {sql}")
        logger.info("=== SQL查询结束（不安全） ===")
        return {
            "success": False,
            "error": "Potentially unsafe query detected. Only SELECT queries are allowed."
        }

    conn = None
    cursor = None
    try:
        conn = get_connection()
        logger.info("数据库连接成功")

        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("START TRANSACTION")
        logger.info("只读事务开始")

        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            conn.commit()

            logger.info("查询执行成功")
            logger.info(f"返回行数: {len(results)}")
            logger.info("=== SQL查询结束 ===")

            return {
                "success": True,
                "results": results,
                "rowCount": len(results)
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"SQL执行错误: {str(e)}")
            logger.info("=== SQL查询结束（失败） ===")
            return {
                "success": False,
                "error": str(e)
            }
    except Exception as e:
        logger.error(f"数据库连接或操作错误: {str(e)}")
        logger.info("=== SQL查询结束（连接失败） ===")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("数据库连接已关闭")


@mcp.resource("mysql://tables")
def get_tables() -> Dict[str, Any]:
    """提供数据库表列表"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [list(table.values())[0] for table in tables]

        return {
            "database": DB_CONFIG["db"],
            "tables": table_names
        }
    finally:
        if cursor:
            cursor.close()
        conn.close()


@mcp.resource("mysql://logs")
def get_logs() -> Dict[str, Any]:
    log_dir = ensure_log_directory()
    log_file = log_dir / f"mcp_mysql_{time.strftime('%Y%m%d')}.log"
    recent_logs = read_log_file(str(log_file), max_lines=100)
    return {
        "count": len(recent_logs),
        "logs": recent_logs
    }



def validate_config():
    """验证环境变量配置"""
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        logger.warning(f"缺失环境变量: {', '.join(missing)}")
        logger.warning("将使用默认值，生产环境可能无法正常工作。")


def main():
    validate_config()
    print(f"MySQL MCP服务器启动，连接到 {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}")


if __name__ == "__main__":
    main()
    mcp.run()
