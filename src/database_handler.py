import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import pymysql

# 确保 logs 目录存在
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "database_handler.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_file,
    filemode='a',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    user: str = os.getenv("DB_USER")
    password: str = os.getenv("DB_PASSWORD")
    db: str = os.getenv("DB_NAME")
    port: int = int(os.getenv("DB_PORT", 3306))
    charset: str = "utf8mb4"

class DatabaseHandler:
    """数据库操作处理器，直接用 pymysql 连接 MySQL"""
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self._schema_cache: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # 缓存5分钟
        self.conn = None

    async def __aenter__(self):
        self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        try:
            self.conn = pymysql.connect(
                host=self.config.host,
                user=self.config.user,
                password=self.config.password,
                db=self.config.db,
                port=self.config.port,
                charset=self.config.charset,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            logger.info("✓ 数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def disconnect(self):
        try:
            if self.conn:
                self.conn.close()
                logger.info("✓ 数据库连接已关闭")
        except Exception as e:
            logger.error(f"断开连接时出错: {e}")

    async def get_schema(self, use_cache: bool = True) -> Dict[str, Any]:
        if use_cache and self._is_cache_valid():
            logger.info("使用缓存的schema信息")
            return self._schema_cache
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_names = [list(table.values())[0] for table in tables]
                schema = {}
                for tname in table_names:
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
                schema_data = {
                    "database": self.config.db,
                    "tables": schema
                }
                self._schema_cache = schema_data
                self._cache_timestamp = datetime.now()
                logger.info("✓ 成功获取数据库schema")
                return schema_data
        except Exception as e:
            logger.error(f"获取schema失败: {e}")
            raise

    async def execute_sql(self, sql: str, page: int = 0, page_size: int = 50) -> Dict[str, Any]:
        try:
            with self.conn.cursor() as cursor:
                # 只允许只读查询
                if not sql.strip().lower().startswith("select"):
                    return {
                        "success": False,
                        "results": None,
                        "error": "只允许SELECT查询",
                        "rowcount": 0,
                        "columns": None
                    }
                cursor.execute(sql)
                results = cursor.fetchall()
                columns = list(results[0].keys()) if results else []
                # 分页
                total_rows = len(results)
                start = page * page_size
                end = start + page_size
                page_data = results[start:end]
                return {
                    "success": True,
                    "results": page_data,
                    "error": None,
                    "rowcount": len(page_data),
                    "columns": columns,
                    "pagination": {
                        "current_page": page,
                        "page_size": page_size,
                        "total_rows": total_rows,
                        "total_pages": (total_rows + page_size - 1) // page_size if total_rows > 0 else 0
                    },
                    "totalRows": total_rows
                }
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            return {
                "success": False,
                "results": None,
                "error": str(e),
                "rowcount": 0,
                "columns": None
            }

    def _is_cache_valid(self) -> bool:
        if not self._schema_cache or not self._cache_timestamp:
            return False
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl

    def format_results(self, query_result: Dict[str, Any], format_type: str = "json") -> str:
        """
        格式化查询结果
        
        Args:
            query_result: 查询结果
            format_type: 格式类型 ("json", "table", "csv")
            
        Returns:
            格式化后的字符串
        """
        if not query_result.get("success"):
            return f"查询失败: {query_result.get('error', '未知错误')}"
        
        results = query_result.get("results", [])
        
        if not results:
            return "查询成功，但没有返回数据"
        
        if format_type == "json":
            return json.dumps(results, indent=2, ensure_ascii=False)
        
        elif format_type == "table":
            if not results:
                return "无数据"
            
            # 获取所有列名
            columns = query_result.get("columns", list(results[0].keys()) if results else [])
            
            # 构建表格
            table_lines = []
            
            # 表头
            header = " | ".join(str(col) for col in columns)
            table_lines.append(header)
            table_lines.append("-" * len(header))
            
            # 数据行
            for row in results:
                if isinstance(row, dict):
                    row_data = " | ".join(str(row.get(col, "")) for col in columns)
                else:
                    row_data = " | ".join(str(val) for val in row)
                table_lines.append(row_data)
            
            return "\n".join(table_lines)
        
        elif format_type == "csv":
            if not results:
                return ""
            
            columns = query_result.get("columns", list(results[0].keys()) if results else [])
            
            csv_lines = []
            
            # CSV表头
            csv_lines.append(",".join(columns))
            
            # CSV数据
            for row in results:
                if isinstance(row, dict):
                    csv_row = ",".join(f'"{str(row.get(col, ""))}"' for col in columns)
                else:
                    csv_row = ",".join(f'"{str(val)}"' for val in row)
                csv_lines.append(csv_row)
            
            return "\n".join(csv_lines)
        
        else:
            return json.dumps(results, indent=2, ensure_ascii=False)

# 便捷函数
async def create_database_handler(config: DatabaseConfig = None) -> DatabaseHandler:
    """创建并连接数据库处理器"""
    handler = DatabaseHandler(config)
    await handler.connect()
    return handler

async def quick_query(sql: str, config: DatabaseConfig = None) -> Dict[str, Any]:
    """快速执行SQL查询"""
    async with DatabaseHandler(config) as db:
        return await db.execute_sql(sql)

async def get_database_schema(config: DatabaseConfig = None) -> Dict[str, Any]:
    """快速获取数据库schema"""
    async with DatabaseHandler(config) as db:
        return await db.get_schema()

if __name__ == "__main__":
    # 测试代码
    async def test():
        try:
            # 测试连接和schema获取
            async with DatabaseHandler() as db:
                print("=== 获取数据库schema ===")
                schema = await db.get_schema()
                print(json.dumps(schema, indent=2, ensure_ascii=False))
                
                print("\n=== 执行测试查询 ===")
                # 这里需要根据你的实际表结构调整SQL
                test_sql = "SHOW TABLES;"
                result = await db.execute_sql(test_sql)
                
                if result["success"]:
                    print("查询成功:")
                    print(db.format_results(result, "table"))
                else:
                    print(f"查询失败: {result['error']}")
                    
        except Exception as e:
            print(f"测试失败: {e}")
    
    asyncio.run(test())