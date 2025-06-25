import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
server_script = project_root / "src" / "mcp-server.py"

async def test_mcp_server():
    """简单测试MCP服务是否正常工作"""
    server_params = StdioServerParameters(
        command="python",
        args=[str(server_script)],
        working_dir=str(project_root)
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✓ MCP服务器连接成功")
                
                # 测试1: 基本查询
                print("\n测试1: 基本连接查询")
                print("正在调用 query_data...")
                result = await session.call_tool("query_data", {"sql": "SELECT 1 as test"})
                print(f"调用完成，结果类型: {type(result)}")
                print(f"结果内容: {result}")
                data = json.loads(result.content[0].text)
                if data.get("success"):
                    print(f"✓ 查询成功: {data['results']}")
                else:
                    print(f"✗ 查询失败: {data.get('error')}")
                
                # 测试2: 获取表列表
                print("\n测试2: 获取数据库表")
                tables = await session.read_resource("mysql://tables")
                tables_data = json.loads(tables.contents[0].text)
                print(f"✓ 数据库: {tables_data.get('database')}")
                print(f"✓ 表数量: {len(tables_data.get('tables', []))}")
                
                # 测试3: 安全检查
                print("\n测试3: 安全检查 (应该被拒绝)")
                unsafe_result = await session.call_tool("query_data", {"sql": "DELETE FROM test"})
                unsafe_data = json.loads(unsafe_result.content[0].text)
                if not unsafe_data.get("success"):
                    print("✓ 不安全查询被正确拒绝")
                else:
                    print("✗ 安全检查失败")
                
                print("\n🎉 所有测试通过，MCP服务正常工作!")
                
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        print("\n检查事项:")
        print("- 确保main.py在当前目录")
        print("- 检查数据库连接配置")
        print("- 确保MySQL服务正在运行")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())