import json
from llm_client import create_llm_client
from database_handler import DatabaseHandler, DatabaseConfig
import asyncio


class SimpleNLQuerySystem:
    def __init__(self, db_config=None, api_key=None):
        self.db_config = db_config or DatabaseConfig()
        self.llm_client = create_llm_client(api_key)
        self.db_handler = DatabaseHandler(self.db_config)

    async def __aenter__(self):
        await self.db_handler.connect()  # ✅ await连接
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db_handler.disconnect()  # ✅ await关闭

    async def query(self, question, use_schema=True):
        schema_info = None
        if use_schema:
            print("获取数据库结构信息...")
            schema_info = await self.db_handler.get_schema()
            print("数据库结构信息获取成功")
        
        print("生成SQL语句...")
        sql = self.llm_client.generate_sql(question, schema_info)
        print(f"生成SQL: {sql}")
        
        print("执行SQL查询...")
        query_result = await self.db_handler.execute_sql(sql)
        
        if query_result["success"]:
            print(f"查询成功，返回 {query_result['rowcount']} 条记录")
        else:
            print(f"查询失败: {query_result['error']}")
        
        return {
            "question": question,
            "sql": sql,
            "query_result": query_result,
            "schema_used": schema_info is not None
        }

    def format_result(self, result):
        if result["query_result"]["success"]:
            return self.db_handler.format_results(result["query_result"], "table")
        else:
            return f"查询失败: {result['query_result']['error']}"
async def main():
    print("自然语言查询系统启动，输入 'quit' 退出，输入 'next' 查看下一页，输入 'prev' 查看上一页")
    
    async with SimpleNLQuerySystem() as system:
        last_sql = None
        last_result = None
        while True:
            question = input("请输入您的问题或命令(next/prev/quit): ").strip()
            if question.lower() in ["quit", "exit", "退出"]:
                break
            if not question:
                continue

            if question.lower() == "next":
                if last_sql is None:
                    print("请先进行一次查询。")
                    continue
                result = await system.db_handler.next_page()
                output = system.db_handler.format_results(result, "table")
                print(output)
                last_result = result
                continue

            if question.lower() == "prev":
                if last_sql is None:
                    print("请先进行一次查询。")
                    continue
                result = await system.db_handler.prev_page()
                output = system.db_handler.format_results(result, "table")
                print(output)
                last_result = result
                continue

            # 正常自然语言查询
            result = await system.query(question)
            output = system.format_result(result)
            print(output)
            # 记录本次SQL
            last_sql = result["sql"]
            last_result = result["query_result"]

if __name__ == "__main__":
    asyncio.run(main())
