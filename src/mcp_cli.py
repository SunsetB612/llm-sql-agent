from mcp_llm_client import create_llm_client
from mcp_http_client import mcp_query, mcp_schema
import time
import uuid

def format_table(results, start_index=1):
    if not results:
        return "无数据"
    
    columns = list(results[0].keys())
    columns = ["编号"] + columns
    
    # 计算每列最大宽度
    col_widths = [max(len("编号"), len(str(start_index + len(results) - 1)))]
    for col in columns[1:]:
        col_widths.append(max(len(str(col)), max(len(str(row.get(col, ""))) for row in results)))
    
    # 表头
    header_cells = [columns[0].ljust(col_widths[0])] + [str(col).ljust(w) for col, w in zip(columns[1:], col_widths[1:])]
    header = "| " + " | ".join(header_cells) + " |"
    
    # 分隔线 - 修复：使用与表头相同的格式
    sep_cells = ["-" * col_widths[0]] + ["-" * w for w in col_widths[1:]]
    sep = "| " + " | ".join(sep_cells) + " |"
    
    # 数据行
    rows = []
    for idx, row in enumerate(results, start=start_index):
        row_cells = [str(idx).ljust(col_widths[0])] + [str(row.get(col, "")).ljust(w) for col, w in zip(columns[1:], col_widths[1:])]
        rows.append("| " + " | ".join(row_cells) + " |")
    
    return "\n".join([header, sep] + rows)

def main():
    print("🚀 智能自然语言查询系统启动")
    print("=" * 50)
    print("📝 使用说明：")
    print("  - 输入自然语言问题，系统会自动生成SQL并执行")
    print("  - 输入 'next' 查看下一页")
    print("  - 输入 'prev' 查看上一页")
    print("  - 输入 'quit' 退出系统")
    print("=" * 50)
    session_id = f"cli_session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    print(f"🆔 会话ID: {session_id}")
    print()
    last_results = None
    last_sql = None
    last_page = 0
    page_size = 50
    while True:
        question = input("🤔 请输入您的问题或命令: ").strip()
        if question.lower() in ["quit", "exit", "退出"]:
            print("👋 感谢使用，再见！")
            break
        if not question:
            continue
        if question.lower() == "next":
            if last_results is None:
                print("❌ 请先进行一次查询。")
                continue
            total_rows = len(last_results)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1
            if last_page + 1 >= total_pages:
                print("❌ 已经是最后一页。")
                continue
            last_page += 1
            start = last_page * page_size
            end = start + page_size
            page_data = last_results[start:end]
            print(f"\n📋 查询结果: (第{last_page+1}/{total_pages}页)")
            print(format_table(page_data, start_index=start+1))
            continue
        if question.lower() == "prev":
            if last_results is None:
                print("❌ 请先进行一次查询。")
                continue
            if last_page == 0:
                print("❌ 已经是第一页。")
                continue
            last_page -= 1
            start = last_page * page_size
            end = start + page_size
            page_data = last_results[start:end]
            print(f"\n📋 查询结果: (第{last_page+1}/{(len(last_results) + page_size - 1) // page_size}页)")
            print(format_table(page_data, start_index=start+1))
            continue
        print(f"\n🔍 处理您的问题: {question}")
        # 获取 schema
        schema_info = mcp_schema()
        # LLM 生成 SQL
        llm_client = create_llm_client()
        sql = llm_client.generate_sql(question, schema_info)
        print(f"生成SQL: {sql}")
        # 通过 MCP HTTP 查询
        query_result = mcp_query(sql, page=0, page_size=1000000, session_id=session_id, user_message=question)
        if query_result.get("success"):
            last_results = query_result.get("results", [])
            last_sql = sql
            last_page = 0
            total_rows = len(last_results)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1
            page_data = last_results[:page_size]
            print(f"\n📋 查询结果: (第1/{total_pages}页)")
            print(format_table(page_data, start_index=1))
            print(f"共 {total_rows} 条记录")
        else:
            print(f"查询失败: {query_result.get('error', '未知错误')}")
            last_results = None
            last_sql = None
            last_page = 0
        print()

if __name__ == "__main__":
    main()
