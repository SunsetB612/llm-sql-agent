import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dataclasses import dataclass
from datetime import datetime

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
    """数据库配置类"""
    server_command: str = "python"
    server_args: List[str] = None
    timeout: int = 30
    
    def __post_init__(self):
        if self.server_args is None:
            self.server_args = ["mcp_server.py"]

class DatabaseHandler:
    """数据库操作处理器，通过MCP与MySQL交互"""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self.session: Optional[ClientSession] = None
        self._schema_cache: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # 缓存5分钟
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.disconnect()
    
    async def connect(self):
        """连接到MCP服务器"""
        try:
            server_params = StdioServerParameters(
                command=self.config.server_command,
                args=self.config.server_args
            )
            
            self.client_context = stdio_client(server_params)
            self.read, self.write = await self.client_context.__aenter__()
            
            self.session_context = ClientSession(self.read, self.write)
            self.session = await self.session_context.__aenter__()
            
            await self.session.initialize()
            logger.info("✓ MCP服务器连接成功")
            
        except Exception as e:
            logger.error(f"连接MCP服务器失败: {e}")
            raise
    
    async def disconnect(self):
        """断开MCP服务器连接"""
        try:
            if hasattr(self, 'session_context') and self.session_context:
                await self.session_context.__aexit__(None, None, None)
            
            if hasattr(self, 'client_context') and self.client_context:
                await self.client_context.__aexit__(None, None, None)
                
            logger.info("✓ MCP服务器连接已断开")
            
        except Exception as e:
            logger.error(f"断开连接时出错: {e}")
    
    async def get_schema(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        获取数据库schema信息
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            数据库结构信息
        """
        # 检查缓存
        if use_cache and self._is_cache_valid():
            logger.info("使用缓存的schema信息")
            return self._schema_cache
        
        try:
            if not self.session:
                raise Exception("数据库连接未建立")
            
            logger.info("正在获取数据库schema...")
            resource = await self.session.read_resource("mysql://schema")
            
            if not resource.contents:
                raise Exception("未能获取到schema信息")
            
            schema_data = json.loads(resource.contents[0].text)
            
            # 更新缓存
            self._schema_cache = schema_data
            self._cache_timestamp = datetime.now()
            
            logger.info("✓ 成功获取数据库schema")
            return schema_data
            
        except Exception as e:
            logger.error(f"获取schema失败: {e}")
            raise
    
    async def next_page(self) -> Dict[str, Any]:
        """获取下一页数据"""
        try:
            if not self.session:
                raise Exception("数据库连接未建立")

            logger.info("请求下一页数据")
            result = await self.session.call_tool("next_page", {})
            
            if not result.content:
                return {
                    "success": False,
                    "error": "未收到响应",
                    "results": None,
                    "rowcount": 0
                }
            
            response_data = json.loads(result.content[0].text)
            return self._format_pagination_result(response_data)
            
        except Exception as e:
            logger.error(f"获取下一页失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": None,
                "rowcount": 0
            }

    async def prev_page(self) -> Dict[str, Any]:
        """获取上一页数据"""
        try:
            if not self.session:
                raise Exception("数据库连接未建立")

            logger.info("请求上一页数据")
            result = await self.session.call_tool("prev_page", {})
            
            if not result.content:
                return {
                    "success": False,
                    "error": "未收到响应",
                    "results": None,
                    "rowcount": 0
                }
            
            response_data = json.loads(result.content[0].text)
            return self._format_pagination_result(response_data)
            
        except Exception as e:
            logger.error(f"获取上一页失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": None,
                "rowcount": 0
            }

    def _format_pagination_result(self, response_data: Dict) -> Dict[str, Any]:
        """格式化分页结果"""
        if response_data.get("success", False):
            results = response_data.get("results", [])
            columns = None
            
            if results and isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], dict):
                    columns = list(results[0].keys())
            
            return {
                "success": True,
                "results": results,
                "error": None,
                "rowcount": len(results) if results else 0,
                "columns": columns,
                "pagination": response_data.get("pagination"),
                "totalRows": response_data.get("totalRows")
            }
        else:
            return {
                "success": False,
                "results": None,
                "error": response_data.get("error", "未知错误"),
                "rowcount": 0,
                "columns": None
            }

    async def execute_sql(self, sql: str, page: int = 0, page_size: int = 50) -> Dict[str, Any]:
        """
        执行SQL查询，支持分页
        """
        try:
            if not self.session:
                raise Exception("数据库连接未建立")

            logger.info(f"执行SQL: {sql}, page: {page}, page_size: {page_size}")
            
            # 通过MCP执行SQL
            result = await self.session.call_tool("query_data", {
                "sql": sql,
                "page": page,
                "page_size": page_size
            })
            
            logger.info(f"MCP返回结果类型: {type(result)}")
            logger.info(f"MCP返回内容: {result}")
            
            if not result.content:
                logger.error("未收到查询结果内容")
                return {
                    "success": False,
                    "results": None,
                    "error": "未收到查询结果",
                    "rowcount": 0,
                    "columns": None
                }
            
            # 打印原始内容用于调试
            raw_content = result.content[0].text
            logger.info(f"原始响应内容: {raw_content}")
            
            # 解析结果
            response_data = json.loads(raw_content)
            
            # 标准化返回格式
            if response_data.get("success", False):
                results = response_data.get("results", [])
                columns = None
                
                # 提取列名（如果有数据的话）
                if results and isinstance(results, list) and len(results) > 0:
                    if isinstance(results[0], dict):
                        columns = list(results[0].keys())
                
                return {
                    "success": True,
                    "results": results,
                    "error": None,
                    "rowcount": len(results) if results else 0,
                    "columns": columns,
                    "pagination": response_data.get("pagination"),
                    "totalRows": response_data.get("totalRows")
                }
            else:
                return {
                    "success": False,
                    "results": None,
                    "error": response_data.get("error", "未知错误"),
                    "rowcount": 0,
                    "columns": None
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始内容: {raw_content if 'raw_content' in locals() else 'N/A'}")
            return {
                "success": False,
                "results": None,
                "error": f"JSON解析失败: {str(e)}",
                "rowcount": 0,
                "columns": None
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
    
    async def query_with_schema(self, sql: str) -> Dict[str, Any]:
        """
        执行SQL查询并附带schema信息
        
        Args:
            sql: SQL语句
            
        Returns:
            包含查询结果和schema信息的字典
        """
        try:
            # 并行获取schema和执行查询
            schema_task = self.get_schema()
            query_task = self.execute_sql(sql)
            
            schema, query_result = await asyncio.gather(schema_task, query_task)
            
            return {
                **query_result,
                "schema": schema,
                "sql": sql
            }
            
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return {
                "success": False,
                "results": None,
                "error": str(e),
                "rowcount": 0,
                "columns": None,
                "schema": None,
                "sql": sql
            }
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
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