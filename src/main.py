import json
from llm_client import create_llm_client
from database_handler import DatabaseHandler, DatabaseConfig
import asyncio
import time
import uuid

# 只保留多轮对话相关功能
from mcp_server import (
    get_or_create_session, 
    cleanup_expired_sessions,
    clear_conversation_context
)

class SimpleNLQuerySystem:
    def __init__(self, db_config=None, api_key=None, session_id=None):
        self.db_config = db_config or DatabaseConfig()
        self.llm_client = create_llm_client(api_key)
        self.db_handler = DatabaseHandler(self.db_config)
        self.session_id = session_id or f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.last_results = None
        self.last_sql = None
        self.last_page = 0
        self.page_size = 50

    def __enter__(self):
        self.db_handler.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db_handler.disconnect()

    def query(self, question, use_schema=True):
        cleanup_expired_sessions()
        session = get_or_create_session(self.session_id)
        schema_info = None
        if use_schema:
            print("获取数据库结构信息...")
            schema_info = asyncio.run(self.db_handler.get_schema())
            print("数据库结构信息获取成功")
        print("生成SQL语句...")
        sql = self.llm_client.generate_sql(question, schema_info)
        print(f"生成SQL: {sql}")
        print("执行SQL查询...")
        # 获取全部结果，便于本地分页
        query_result = asyncio.run(self.db_handler.execute_sql(sql, page=0, page_size=1000000))
        session.add_context(sql, query_result, question)
        if query_result["success"]:
            print(f"查询成功，返回 {query_result['rowcount']} 条记录")
            self.last_results = query_result["results"]
            self.last_sql = sql
            self.last_page = 0
        else:
            print(f"查询失败: {query_result['error']}")
            self.last_results = None
            self.last_sql = None
            self.last_page = 0
        # 返回第一页的分页结果
        page_result = self.get_page(0)
        return {
            "question": question,
            "sql": sql,
            "query_result": page_result,
            "schema_used": schema_info is not None,
            "session_id": self.session_id
        }

    def get_page(self, page):
        if self.last_results is None:
            return {
                "success": False,
                "results": None,
                "error": "没有可分页的数据，请先查询。",
                "rowcount": 0,
                "columns": None
            }
        total_rows = len(self.last_results)
        start = page * self.page_size
        end = start + self.page_size
        page_data = self.last_results[start:end]
        columns = list(self.last_results[0].keys()) if self.last_results else []
        return {
            "success": True,
            "results": page_data,
            "error": None,
            "rowcount": len(page_data),
            "columns": columns,
            "pagination": {
                "current_page": page,
                "page_size": self.page_size,
                "total_rows": total_rows,
                "total_pages": (total_rows + self.page_size - 1) // self.page_size if total_rows > 0 else 0
            },
            "totalRows": total_rows
        }

    def next_page(self):
        if self.last_results is None:
            return self.get_page(0)
        total_rows = len(self.last_results)
        total_pages = (total_rows + self.page_size - 1) // self.page_size if total_rows > 0 else 0
        if self.last_page + 1 >= total_pages:
            print("❌ 已经是最后一页。")
            return None
        self.last_page += 1
        return self.get_page(self.last_page)

    def prev_page(self):
        if self.last_results is None:
            return self.get_page(0)
        if self.last_page == 0:
            print("❌ 已经是第一页。")
            return None
        self.last_page -= 1
        return self.get_page(self.last_page)

    def format_result(self, result):
        if result["query_result"]["success"]:
            return self.db_handler.format_results(result["query_result"], "table")
        else:
            return f"查询失败: {result['query_result']['error']}"

def main():
    print("🚀 智能自然语言查询系统启动")
    print("=" * 50)
    print("📝 使用说明：")
    print("  - 输入自然语言问题，系统会自动生成SQL并执行")
    print("  - 输入 'next' 查看下一页")
    print("  - 输入 'prev' 查看上一页")
    print("  - 输入 'context' 查看对话上下文")
    print("  - 输入 'clear' 清理当前会话")
    print("  - 输入 'quit' 退出系统")
    print("=" * 50)
    session_id = f"interactive_session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    print(f"🆔 会话ID: {session_id}")
    print()
    with SimpleNLQuerySystem(session_id=session_id) as system:
        last_sql = None
        last_result = None
        while True:
            question = input("🤔 请输入您的问题或命令: ").strip()
            if question.lower() in ["quit", "exit", "退出"]:
                print("👋 感谢使用，再见！")
                break
            if not question:
                continue
            if question.lower() == "next":
                result = system.next_page()
                if result is None:
                    continue
                output = system.db_handler.format_results(result, "table")
                print(output)
                last_result = result
                continue
            if question.lower() == "prev":
                result = system.prev_page()
                if result is None:
                    continue
                output = system.db_handler.format_results(result, "table")
                print(output)
                last_result = result
                continue
            if question.lower() == "context":
                from mcp_server import get_conversation_context
                context = get_conversation_context(session_id)
                if context.get('success'):
                    ctx_info = context['context']
                    print(f"\n📊 会话上下文信息：")
                    print(f"  会话ID: {ctx_info['session_id']}")
                    print(f"  总查询数: {ctx_info['metadata']['total_queries']}")
                    print(f"  成功查询数: {ctx_info['metadata']['successful_queries']}")
                    print(f"  失败查询数: {ctx_info['metadata']['failed_queries']}")
                    if ctx_info['recent_queries']:
                        print(f"\n📝 最近的查询：")
                        for i, query in enumerate(ctx_info['recent_queries'], 1):
                            print(f"  {i}. 问题: {query['user_message']}")
                            print(f"     SQL: {query['sql']}")
                            print(f"     结果: {'✅ 成功' if query['success'] else '❌ 失败'}")
                            print()
                else:
                    print("❌ 获取上下文失败")
                continue
            if question.lower() == "clear":
                clear_conversation_context(session_id)
                print("🧹 会话上下文已清理")
                continue
            print(f"\n🔍 处理您的问题: {question}")
            result = system.query(question)
            output = system.format_result(result)
            print(f"\n📋 查询结果:")
            print(output)
            last_sql = result["sql"]
            last_result = result["query_result"]
            print()

if __name__ == "__main__":
    main()
