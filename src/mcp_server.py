from typing import Any, Dict, List
import os
import logging
import time
from pathlib import Path
import re
from collections import deque

import MySQLdb
import MySQLdb.cursors

from mcp.server.fastmcp import FastMCP
import dotenv
import libinjection

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

# ----- 分页状态管理 -----
pagination_state = {
    "last_sql": "",
    "last_results": None,
    "current_page": 0,
    "page_size": 50,  # 每页显示行数
    "total_rows": 0
}

# ----- 对话上下文管理 -----
# 存储所有活跃的对话会话
conversation_sessions = {}

# 每个会话的最大上下文长度
MAX_CONTEXT_LENGTH = 10

# 上下文过期时间（秒）
CONTEXT_EXPIRE_TIME = 3600  # 1小时

class ConversationSession:
    """对话会话管理类"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context = deque(maxlen=MAX_CONTEXT_LENGTH)
        self.last_activity = time.time()
        self.metadata = {
            "created_at": time.time(),
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0
        }
    
    def add_context(self, sql: str, result: Dict[str, Any], user_message: str = ""):
        """添加上下文信息"""
        context_item = {
            "timestamp": time.time(),
            "sql": sql,
            "result": result,
            "user_message": user_message,
            "success": result.get("success", False)
        }
        self.context.append(context_item)
        self.last_activity = time.time()
        
        # 更新统计信息
        self.metadata["total_queries"] += 1
        if result.get("success", False):
            self.metadata["successful_queries"] += 1
        else:
            self.metadata["failed_queries"] += 1
    
    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "session_id": self.session_id,
            "context_length": len(self.context),
            "last_activity": self.last_activity,
            "metadata": self.metadata,
            "recent_queries": list(self.context)[-3:] if self.context else []  # 最近3个查询
        }
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return time.time() - self.last_activity > CONTEXT_EXPIRE_TIME

def get_or_create_session(session_id: str) -> ConversationSession:
    """获取或创建会话"""
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = ConversationSession(session_id)
    return conversation_sessions[session_id]

def cleanup_expired_sessions():
    """清理过期的会话"""
    expired_sessions = []
    for session_id, session in conversation_sessions.items():
        if session.is_expired():
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del conversation_sessions[session_id]
        logger.info(f"清理过期会话: {session_id}")

# ----- 对话上下文管理结束 -----

SENSITIVE_FIELDS = ['password', 'salary', 'ssn', 'credit_card']

def reset_pagination():
    """重置分页状态"""
    pagination_state["last_sql"] = ""
    pagination_state["last_results"] = None
    pagination_state["current_page"] = 0
    pagination_state["total_rows"] = 0

def get_page_data(results: List[Dict], page: int, page_size: int) -> Dict[str, Any]:
    """获取指定页的数据"""
    total_rows = len(results)
    total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0
    
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_rows)
    
    page_data = results[start_idx:end_idx] if start_idx < total_rows else []
    
    return {
        "data": page_data,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "page_size": page_size,
            "total_rows": total_rows,
            "has_next": page < total_pages - 1,
            "has_prev": page > 0,
            "showing_rows": f"{start_idx + 1}-{end_idx}" if page_data else "0-0"
        }
    }
# ----- 分页功能结束 -----

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

MAX_LOG_LINES = 2000  # 日志最大保留行数

def trim_log_file(log_file: Path, max_lines: int = MAX_LOG_LINES):
    """修剪日志文件，只保留最新max_lines行"""
    if not log_file.exists():
        return
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if len(lines) > max_lines:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.writelines(lines[-max_lines:])

def setup_logger():
    """设置日志配置，日志追加写入"""
    log_dir = ensure_log_directory()
    log_file = log_dir / f"mcp_mysql_{time.strftime('%Y%m%d')}.log"

    logger = logging.getLogger('mysql-mcp-server')
    logger.setLevel(logging.INFO)

    # 彻底清空所有 handler（包括 root logger 继承的）
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    # 也清空 root logger 的 handler
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    class TrimmingFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            try:
                trim_log_file(log_file, MAX_LOG_LINES)
            except Exception:
                pass

    file_handler = TrimmingFileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    # 不加 console_handler

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
    """提供数据库表结构信息（全部表）"""
    return get_schema_filtered()

def get_schema_filtered(table_name: str = None) -> Dict[str, Any]:
    """提供数据库表结构信息，支持按表名过滤（仅本地/测试用）"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [list(table.values())[0] for table in tables]
        schema = {}
        for tname in table_names:
            if table_name and tname != table_name:
                continue
            cursor.execute(f"DESCRIBE `{tname}`")
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
            schema[tname] = table_schema
        return {
            "database": DB_CONFIG["db"],
            "tables": schema
        }
    finally:
        if cursor:
            cursor.close()
        conn.close()


def is_safe_query(sql: str) -> bool:
    sql_lower = sql.lstrip().lower()
    allowed_prefixes = ["select", "show", "desc", "describe", "explain"]
    for prefix in allowed_prefixes:
        if re.match(rf"^{prefix}(\s|\(|\*|\b)", sql_lower):
            break
    else:
        return False
    dangerous_keywords = [
        'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'truncate', 'replace', 'merge', 'call', 'exec', 'execute'
    ]
    if any(keyword in sql_lower for keyword in dangerous_keywords):
        return False
    return True

@mcp.tool()
def next_page() -> Dict[str, Any]:
    """获取下一页数据"""
    if not pagination_state["last_results"]:
        return {
            "success": False,
            "error": "No previous query results to paginate"
        }
    
    current_page = pagination_state["current_page"]
    page_info = get_page_data(
        pagination_state["last_results"], 
        current_page + 1, 
        pagination_state["page_size"]
    )
    
    # 修复逻辑错误：检查是否有下一页
    if not page_info["pagination"]["has_next"]:
        return {
            "success": False,
            "error": "Already at the last page"
        }
    
    pagination_state["current_page"] = current_page + 1
    
    logger.info(f"获取下一页: 第{pagination_state['current_page'] + 1}页")
    
    return {
        "success": True,
        "results": page_info["data"],
        "rowCount": len(page_info["data"]),
        "totalRows": pagination_state["total_rows"],
        "pagination": page_info["pagination"]
    }

@mcp.tool()
def prev_page() -> Dict[str, Any]:
    """获取上一页数据"""
    if not pagination_state["last_results"]:
        return {
            "success": False,
            "error": "No previous query results to paginate"
        }
    
    current_page = pagination_state["current_page"]
    if current_page <= 0:
        return {
            "success": False,
            "error": "Already at the first page"
        }
    
    pagination_state["current_page"] = current_page - 1
    page_info = get_page_data(
        pagination_state["last_results"], 
        pagination_state["current_page"], 
        pagination_state["page_size"]
    )
    
    logger.info(f"获取上一页: 第{pagination_state['current_page'] + 1}页")
    
    return {
        "success": True,
        "results": page_info["data"],
        "rowCount": len(page_info["data"]),
        "pagination": page_info["pagination"]
    }

def contains_sensitive_field(sql: str) -> bool:
    sql_lower = sql.lower()
    for field in SENSITIVE_FIELDS:
        # 匹配字段名，防止误判
        if re.search(r'\b' + re.escape(field.lower()) + r'\b', sql_lower):
            return True
    return False

def is_sql_injection(sql: str) -> bool:
    """
    简易 SQL 注入检测。
    利用 libinjection 库和常见注入特征模式，拦截明显的拼接注入或关键词注入攻击。
    返回 True 表示检测到注入风险，False 表示未检测到。
    """
    sql_lower = sql.strip().lower()
    try:
        # 1. 使用 libinjection 库检测
        result = libinjection.is_sql_injection(sql)
        if result.get('is_sqli', False):
            # 2. 进一步用正则检测常见注入特征
            injection_patterns = [
                r'or\s*1\s*=\s*1',
                r'union\s+select',
                r';\s*drop\s+',
                r';\s*insert\s+',
                r';\s*update\s+',
                r';\s*delete\s+',
                r'and\s+sleep\s*\(',
                r'benchmark\s*\(',
                r'and\s*\(\s*select',
                r'and\s+exists\s*\(',
                r'and\s*\(\s*1\s*=\s*1',
                r'or\s*\(\s*1\s*=\s*1',
                r'or\s*1\s*=\s*1--',
                r'or\s*1\s*=\s*1#',
                # 可继续补充
            ]
            for pattern in injection_patterns:
                if re.search(pattern, sql_lower):
                    return True
            # 没有明显注入特征，放行
            return False
        return False
    except Exception as e:
        logger.warning(f"SQL注入检测失败: {e}")
        return False

@mcp.tool()
def query_data(sql: str, page: int = 0, page_size: int = 50, session_id: str = "default", user_message: str = "") -> Dict[str, Any]:
    """执行只读SQL查询，支持分页和多轮对话上下文"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    logger.info("=== 新的SQL查询开始 ===")
    logger.info(f"时间戳: {timestamp}")
    logger.info(f"会话ID: {session_id}")
    logger.info(f"SQL语句: {sql}")
    logger.info(f"用户消息: {user_message}")
    logger.info(f"请求页码: {page}, 页大小: {page_size}")

    # 清理过期会话
    cleanup_expired_sessions()
    
    # 获取或创建会话
    session = get_or_create_session(session_id)

    # 只读 SQL 白名单过滤
    if not is_safe_query(sql):
        logger.warning(f"不安全查询被拒绝: {sql}")
        logger.info("=== SQL查询结束（不安全） ===")
        result = {
            "success": False,
            "error": "只允许只读查询（SELECT）"
        }
        logger.info(f"返回结果: {result}")
        # 记录到上下文
        session.add_context(sql, result, user_message)
        return result

    # SQL 注入检测
    if is_sql_injection(sql):
        logger.warning(f"检测到疑似SQL注入被拒绝: {sql}")
        result = {
            "success": False,
            "error": "检测到疑似SQL注入，已拒绝执行"
        }
        # 记录到上下文
        session.add_context(sql, result, user_message)
        return result

    # 敏感字段检测
    if contains_sensitive_field(sql):
        logger.warning(f"查询包含敏感字段被拒绝: {sql}")
        result = {
            "success": False,
            "error": "查询包含敏感字段，已拒绝执行"
        }
        # 记录到上下文
        session.add_context(sql, result, user_message)
        return result

    try:
        # 如果是新查询，重置分页状态
        # 安全获取last_sql，确保不是None
        last_sql = pagination_state.get("last_sql") or ""
        if sql.strip().lower() != last_sql.strip().lower():
            reset_pagination()
            pagination_state["last_sql"] = sql.strip().lower()
            pagination_state["page_size"] = page_size
            logger.info("重置分页状态，这是新查询")
        else:
            # 如果是同一个查询但指定了不同的页码，更新当前页
            pagination_state["current_page"] = page
            logger.info(f"相同查询，更新页码到: {page}")

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
                logger.info(f"返回总行数: {len(results)}")

                # 保存完整结果用于分页
                pagination_state["last_results"] = results
                pagination_state["total_rows"] = len(results)

                # 获取当前页数据
                page_info = get_page_data(results, page, page_size)

                logger.info(f"分页信息: 第{page + 1}页，共{page_info['pagination']['total_pages']}页，显示行 {page_info['pagination']['showing_rows']}")
                
                result = {
                    "success": True,
                    "results": page_info["data"],
                    "rowCount": len(page_info["data"]),
                    "totalRows": page_info["pagination"]["total_rows"],
                    "pagination": page_info["pagination"]
                }
                
                logger.info("=== SQL查询结束 ===")
                logger.info(f"返回结果长度: {len(str(result))}")
                # 记录到上下文
                session.add_context(sql, result, user_message)
                return result
                
            except Exception as e:
                conn.rollback()
                logger.error(f"SQL执行错误: {str(e)}")
                logger.info("=== SQL查询结束（SQL执行失败） ===")
                result = {
                    "success": False,
                    "error": str(e)
                }
                logger.info(f"返回错误结果: {result}")
                # 记录到上下文
                session.add_context(sql, result, user_message)
                return result
                
        except Exception as e:
            logger.error(f"数据库连接或操作错误: {str(e)}")
            logger.info("=== SQL查询结束（连接失败） ===")
            result = {
                "success": False,
                "error": str(e)
            }
            logger.info(f"返回连接错误结果: {result}")
            # 记录到上下文
            session.add_context(sql, result, user_message)
            return result
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            logger.info("数据库连接已关闭")
            
    except Exception as e:
        logger.error(f"query_data函数异常: {str(e)}")
        result = {
            "success": False,
            "error": f"Internal error: {str(e)}"
        }
        logger.info(f"返回异常结果: {result}")
        # 记录到上下文
        session.add_context(sql, result, user_message)
        return result


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


@mcp.tool()
def get_conversation_context(session_id: str = "default") -> Dict[str, Any]:
    """获取指定会话的上下文信息"""
    cleanup_expired_sessions()
    
    if session_id not in conversation_sessions:
        return {
            "success": False,
            "error": f"会话 {session_id} 不存在"
        }
    
    session = conversation_sessions[session_id]
    return {
        "success": True,
        "context": session.get_context_summary()
    }


@mcp.tool()
def clear_conversation_context(session_id: str = "default") -> Dict[str, Any]:
    """清理指定会话的上下文"""
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
        logger.info(f"清理会话上下文: {session_id}")
        return {
            "success": True,
            "message": f"会话 {session_id} 上下文已清理"
        }
    else:
        return {
            "success": False,
            "error": f"会话 {session_id} 不存在"
        }


@mcp.tool()
def list_active_sessions() -> Dict[str, Any]:
    """列出所有活跃的会话"""
    cleanup_expired_sessions()
    
    active_sessions = []
    for session_id, session in conversation_sessions.items():
        active_sessions.append({
            "session_id": session_id,
            "context_length": len(session.context),
            "last_activity": session.last_activity,
            "metadata": session.metadata
        })
    
    return {
        "success": True,
        "active_sessions": active_sessions,
        "total_sessions": len(active_sessions)
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

# === 新增 HTTP API 服务 ===
try:
    from flask import Flask, request, jsonify
    app = Flask(__name__)

    @app.route('/query', methods=['POST'])
    def http_query():
        data = request.json
        sql = data.get('sql')
        page = data.get('page', 0)
        page_size = data.get('page_size', 50)
        session_id = data.get('session_id', 'default')
        user_message = data.get('user_message', '')
        result = query_data(sql, page, page_size, session_id, user_message)
        return jsonify(result)

    @app.route('/schema', methods=['GET'])
    def http_schema():
        table = request.args.get('table')
        return jsonify(get_schema_filtered(table))

    @app.route('/logs', methods=['GET'])
    def http_logs():
        return jsonify(get_logs())

    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=8000)
except ImportError:
    pass
