import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mcp_server import contains_sensitive_field, query_data

if __name__ == "__main__":
    test_sqls = [
        "SELECT password FROM user;",
        "SELECT name, salary FROM employee;",
        "SELECT ssn FROM person;",
        "SELECT credit_card FROM payment;",
        "SELECT name FROM student;",
        "SELECT * FROM course;"
    ]
    print("SQL被拒绝执行情况 (True=被拒绝, False=允许):")
    for sql in test_sqls:
        result = query_data(sql)
        rejected = not result.get('success', False)
        print(f"SQL: {sql}\n被拒绝: {rejected}\n{'-'*40}") 