import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mcp_server import query_data, get_conversation_context, get_conversation_suggestions, clear_conversation_context
import time
import uuid

def interactive_demo():
    """交互式多轮对话演示"""
    session_id = f"demo_session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    print("🚀 多轮对话演示系统")
    print("=" * 50)
    print("📝 使用说明：")
    print("  - 输入SQL查询语句")
    print("  - 输入 'context' 查看对话上下文")
    print("  - 输入 'suggest' 获取查询建议")
    print("  - 输入 'clear' 清理当前会话")
    print("  - 输入 'quit' 退出系统")
    print("=" * 50)
    print(f"🆔 会话ID: {session_id}")
    print()
    
    # 显示初始建议
    print("💡 您可以尝试以下查询：")
    print("  - SELECT * FROM student LIMIT 3")
    print("  - SELECT * FROM course LIMIT 2")
    print("  - SELECT COUNT(*) FROM student")
    print("  - SHOW TABLES")
    print()
    
    while True:
        user_input = input("🤔 请输入SQL查询或命令: ").strip()
        
        if user_input.lower() in ["quit", "exit", "退出"]:
            print("👋 感谢使用，再见！")
            break
            
        if not user_input:
            continue
            
        if user_input.lower() == "context":
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
                        print(f"  {i}. 用户消息: {query['user_message']}")
                        print(f"     SQL: {query['sql']}")
                        print(f"     结果: {'✅ 成功' if query['success'] else '❌ 失败'}")
                        print()
            else:
                print("❌ 获取上下文失败")
            continue
            
        if user_input.lower() == "suggest":
            suggestions = get_conversation_suggestions(session_id)
            if suggestions.get('success'):
                print(f"\n💡 为会话 {suggestions['session_id']} 提供的建议：")
                for i, suggestion in enumerate(suggestions['suggestions'], 1):
                    print(f"  {i}. {suggestion['description']}")
                    print(f"     SQL: {suggestion['suggestion']}")
                    print()
            else:
                print("❌ 获取建议失败")
            continue
            
        if user_input.lower() == "clear":
            clear_conversation_context(session_id)
            print("🧹 会话上下文已清理")
            continue
        
        # 执行SQL查询
        print(f"\n🔍 执行查询: {user_input}")
        result = query_data(
            sql=user_input,
            session_id=session_id,
            user_message=user_input
        )
        
        if result.get('success'):
            print(f"✅ 查询成功！")
            print(f"📊 返回 {result.get('rowCount', 0)} 行数据")
            
            # 显示结果（简化显示）
            results = result.get('results', [])
            if results:
                print(f"\n📋 查询结果（前3行）:")
                for i, row in enumerate(results[:3], 1):
                    print(f"  行{i}: {row}")
                if len(results) > 3:
                    print(f"  ... 还有 {len(results) - 3} 行数据")
            else:
                print("📋 查询结果为空")
        else:
            print(f"❌ 查询失败: {result.get('error', '未知错误')}")
        
        print()
        
        # 显示相关建议
        suggestions = get_conversation_suggestions(session_id)
        if suggestions.get('success') and suggestions['suggestions']:
            print("💡 基于您的查询历史，以下是一些建议：")
            for i, suggestion in enumerate(suggestions['suggestions'][:2], 1):
                print(f"  {i}. {suggestion['description']}")
            print("   您可以尝试这些查询，或者继续输入您的SQL。")
        print()

if __name__ == "__main__":
    interactive_demo() 