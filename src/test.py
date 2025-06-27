from mcp_llm_client import create_llm_client
from mcp_http_client import mcp_query, mcp_schema

def format_table(results):
    if not results:
        return "无数据"
    
    columns = list(results[0].keys())
    
    # 计算每列最大宽度
    col_widths = []
    for col in columns:
        col_widths.append(max(len(str(col)), max(len(str(row.get(col, ""))) for row in results)))
    
    # 表头
    header_cells = [str(col).ljust(w) for col, w in zip(columns, col_widths)]
    header = "| " + " | ".join(header_cells) + " |"
    
    # 分隔线
    sep_cells = ["-" * w for w in col_widths]
    sep = "| " + " | ".join(sep_cells) + " |"
    
    # 数据行
    rows = []
    for row in results:
        row_cells = [str(row.get(col, "")).ljust(w) for col, w in zip(columns, col_widths)]
        rows.append("| " + " | ".join(row_cells) + " |")
    
    return "\n".join([header, sep] + rows)

def main():
    print("🚀 智能自然语言查询系统启动")
    print("=" * 50)
    print("📝 使用说明：")
    print("  - 输入自然语言问题，系统会自动生成SQL并执行")
    print("  - 输入 'quit' 退出系统")
    print("=" * 50)
    print()
    
    while True:
        question = input("🤔 请输入您的问题: ").strip()
        
        if question.lower() in ["quit", "exit", "退出"]:
            print("👋 感谢使用，再见！")
            break
            
        if not question:
            continue
        
        print(f"\n🔍 处理您的问题: {question}")
        
        # 获取 schema
        schema_info = mcp_schema()
        
        # LLM 生成 SQL
        llm_client = create_llm_client()
        sql = llm_client.generate_sql(question, schema_info)
        print(f"生成SQL: {sql}")
        
        # 通过 MCP HTTP 查询
        query_result = mcp_query(sql)
        
        if query_result.get("success"):
            results = query_result.get("results", [])
            print(f"\n📋 查询结果:")
            print(format_table(results))
            print(f"共 {len(results)} 条记录")
        else:
            print(f"❌ 查询失败: {query_result.get('error', '未知错误')}")
        
        print()

if __name__ == "__main__":
    main()