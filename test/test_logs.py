from typing import Any, Dict
import os 
import logging

import MySQLdb  
from mcp.server.fastmcp import FastMCP

import dotenv 
dotenv.load_dotenv()

import time #时间戳
from typing import Any, Dict, List


# Create MCP server instance
mcp = FastMCP("mysql-server")

# Database connection configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER"),
    "passwd": os.getenv("DB_PASSWORD"), 
    "db": os.getenv("DB_NAME"),  
    "port": int(os.getenv("DB_PORT", 3306))
}

# 配置日志
log_file_path = 'mysql_queries.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger("mysql-mcp-server")

# 程序启动时测试日志是否正常工作
logger.info("MySQL MCP Server logging system initialized")
print(f"日志文件路径: {os.path.abspath(log_file_path)}")

# 新增：内存日志列表，存放历史查询记录
query_logs: List[Dict[str, Any]] = []

# Connect to MySQL database
def get_connection():
    try:
        return MySQLdb.connect(**DB_CONFIG)
    except MySQLdb.Error as e:
        print(f"Database connection error: {e}")
        raise


@mcp.resource("mysql://schema")
def get_schema() -> Dict[str, Any]:
    """Provide database table structure information"""
    conn = get_connection()
    cursor = None
    try:
        # Create dictionary cursor
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        # Get all table names
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [list(table.values())[0] for table in tables]
        
        # Get structure for each table
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
    """Basic check for potentially unsafe queries"""
    sql_lower = sql.lower()
    unsafe_keywords = ["insert", "update", "delete", "drop", "alter", "truncate", "create"]
    return not any(keyword in sql_lower for keyword in unsafe_keywords)


@mcp.tool()
def query_data(sql: str) -> Dict[str, Any]:
    """Execute read-only SQL queries"""
    if not is_safe_query(sql):
        return {
            "success": False,
            "error": "Potentially unsafe query detected. Only SELECT queries are allowed."
        }
    
    # 记录查询到日志系统
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    logger.info(f"SQL Query - Timestamp: {timestamp}, SQL: {sql}")
    
    conn = get_connection()
    cursor = None
    try:
        # Create dictionary cursor
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        # Start read-only transaction
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("START TRANSACTION")
        
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            conn.commit()

            # 新增：记录日志，时间戳精确到秒
            query_logs.append({
                "timestamp": timestamp,
                "sql": sql
            })
            
            # 记录查询执行成功到日志系统
            logger.info(f"SQL Query Success - Rows returned: {len(results)}")
            
            # Convert results to serializable format
            return {
                "success": True,
                "results": results,
                "rowCount": len(results)
            }
        except Exception as e:
            conn.rollback()
            # 记录查询执行失败到日志系统
            logger.error(f"SQL Query Error - {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    finally:
        if cursor:
            cursor.close()
        conn.close()


@mcp.resource("mysql://tables")
def get_tables() -> Dict[str, Any]:
    """Provide database table list"""
    conn = get_connection()
    cursor = None
    try:
        # Create dictionary cursor
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

@mcp.tool()
def test_logging() -> Dict[str, Any]:
    """测试日志写入功能"""
    test_message = f"Test log entry at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
    logger.info(test_message)
    print(f"已写入测试日志: {test_message}")
    
    return {
        "success": True,
        "message": "Test log written",
        "log_file": os.path.abspath('mysql_queries.log')
    }
def get_logs() -> Dict[str, Any]:
    """返回最近的查询日志，按时间倒序"""
    # 返回最近100条日志（防止内存过大）
    recent_logs = query_logs[-100:]
    recent_logs.reverse()  # 最近的排前面
    return {
        "count": len(recent_logs),
        "logs": recent_logs
    }


def validate_config():
    """Validate database configuration"""
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.warning(f"Missing environment variables: {', '.join(missing)}")
        logger.warning("Using default values, which may not work in production.")


def main():
    validate_config()
    logger.info("MySQL MCP Server started successfully")
    print(f"MySQL MCP server started, connected to {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}")
    print(f"日志文件位置: {os.path.abspath('mysql_queries.log')}")
    
    # 测试日志写入
    logger.info("Server initialization completed - ready to accept queries")


if __name__ == "__main__":
    main()
    mcp.run()