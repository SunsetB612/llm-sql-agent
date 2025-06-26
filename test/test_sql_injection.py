import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mcp_server import is_sql_injection, query_data

if __name__ == "__main__":
    test_sqls = [
        # 正常查询
        "SELECT * FROM student;",
        "SELECT * FROM course;",
        
        # 注入攻击测试
        "SELECT * FROM user WHERE id=1 OR 1=1;",
        "SELECT * FROM user WHERE id=1 OR 1=1 --",
        "SELECT * FROM user WHERE id=1; DROP TABLE user;",
        "SELECT * FROM user UNION SELECT * FROM admin;",
        "SELECT * FROM user WHERE id=1 AND SLEEP(5);",
        "SELECT * FROM user WHERE id=1 AND BENCHMARK(1000000,MD5(1));",
        "SELECT * FROM user WHERE id=1 # 注释",
        "SELECT * FROM user WHERE id=1; INSERT INTO user VALUES(1,'hack');",
        "SELECT * FROM user WHERE id=1; UPDATE user SET password='hack';",
        "SELECT * FROM user WHERE id=1; DELETE FROM user;",
    ]
    
    print("SQL注入检测和拦截结果:")
    print("SQL | 注入检测 | 被拒绝 | 拒绝原因")
    print("-" * 80)
    
    for sql in test_sqls:
        injection_detected = is_sql_injection(sql)
        result = query_data(sql)
        rejected = not result.get('success', False)
        reason = result.get('error', '') if rejected else ''
        
        print(f"{sql} | {injection_detected} | {rejected} | {reason}") 