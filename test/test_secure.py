import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mcp_server import is_safe_query

if __name__ == "__main__":
    test_sqls = [
        "SELECT * FROM student;",
        "select name from course;",
        "SHOW TABLES;",
        "DESC student;",
        "EXPLAIN SELECT * FROM student;",
        "DELETE FROM student WHERE id=1;",
        "UPDATE student SET name='abc' WHERE id=1;",
        "INSERT INTO student (id, name) VALUES (1, 'abc');",
        "DROP TABLE student;",
        "ALTER TABLE student ADD COLUMN age INT;"
    ]
    for sql in test_sqls:
        result = is_safe_query(sql)
        print(f"SQL: {sql}\n允许执行: {result}\n{'-'*40}") 