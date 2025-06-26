import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mcp_server import query_data, get_conversation_context, list_active_sessions, clear_conversation_context

def test_conversation_context():
    """测试多轮对话上下文功能"""
    session_id = "test_session_001"
    
    print("=== 多轮对话上下文测试 ===")
    print(f"会话ID: {session_id}")
    print()
    
    # 第一轮查询
    print("第1轮查询: 查看学生表")
    result1 = query_data(
        sql="SELECT * FROM student LIMIT 3",
        session_id=session_id,
        user_message="我想看看学生表里有什么数据"
    )
    print(f"结果: {result1.get('success')}, 返回行数: {result1.get('rowCount', 0)}")
    print()
    
    # 第二轮查询
    print("第2轮查询: 查看课程表")
    result2 = query_data(
        sql="SELECT * FROM course LIMIT 2",
        session_id=session_id,
        user_message="现在我想看看课程表"
    )
    print(f"结果: {result2.get('success')}, 返回行数: {result2.get('rowCount', 0)}")
    print()
    
    # 第三轮查询 - 基于前两轮的上下文
    print("第3轮查询: 统计学生数量")
    result3 = query_data(
        sql="SELECT COUNT(*) as student_count FROM student",
        session_id=session_id,
        user_message="我想知道总共有多少学生"
    )
    print(f"结果: {result3.get('success')}, 返回行数: {result3.get('rowCount', 0)}")
    print()
    
    # 获取会话上下文
    print("获取会话上下文:")
    context = get_conversation_context(session_id)
    if context.get('success'):
        ctx_info = context['context']
        print(f"会话ID: {ctx_info['session_id']}")
        print(f"上下文长度: {ctx_info['context_length']}")
        print(f"总查询数: {ctx_info['metadata']['total_queries']}")
        print(f"成功查询数: {ctx_info['metadata']['successful_queries']}")
        print(f"失败查询数: {ctx_info['metadata']['failed_queries']}")
        print()
        
        print("最近的查询:")
        for i, query in enumerate(ctx_info['recent_queries'], 1):
            print(f"  {i}. SQL: {query['sql']}")
            print(f"     用户消息: {query['user_message']}")
            print(f"     成功: {query['success']}")
            print()
    else:
        print(f"获取上下文失败: {context.get('error')}")
    
    # 列出活跃会话
    print("活跃会话列表:")
    sessions = list_active_sessions()
    if sessions.get('success'):
        print(f"总活跃会话数: {sessions['total_sessions']}")
        for session in sessions['active_sessions']:
            print(f"  会话ID: {session['session_id']}")
            print(f"  上下文长度: {session['context_length']}")
            print(f"  总查询数: {session['metadata']['total_queries']}")
            print()
    else:
        print(f"获取会话列表失败: {sessions.get('error')}")

def test_multiple_sessions():
    """测试多个会话的独立性"""
    print("=== 多会话独立性测试 ===")
    
    # 会话1
    session1 = "session_1"
    result1 = query_data(
        sql="SELECT * FROM student LIMIT 1",
        session_id=session1,
        user_message="会话1的查询"
    )
    
    # 会话2
    session2 = "session_2"
    result2 = query_data(
        sql="SELECT * FROM course LIMIT 1",
        session_id=session2,
        user_message="会话2的查询"
    )
    
    # 检查会话独立性
    context1 = get_conversation_context(session1)
    context2 = get_conversation_context(session2)
    
    print(f"会话1上下文长度: {context1['context']['context_length'] if context1.get('success') else 0}")
    print(f"会话2上下文长度: {context2['context']['context_length'] if context2.get('success') else 0}")
    
    # 清理测试会话
    clear_conversation_context(session1)
    clear_conversation_context(session2)
    print("测试会话已清理")

if __name__ == "__main__":
    test_conversation_context()
    print("\n" + "="*50 + "\n")
    test_multiple_sessions() 