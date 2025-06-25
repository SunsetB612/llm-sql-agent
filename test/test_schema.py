import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mcp_server import get_schema_filtered

if __name__ == "__main__":
    print("=== 获取所有表结构 ===")
    all_schema = get_schema_filtered()
    print(all_schema)

    print("\n=== 获取 student 表结构 ===")
    student_schema = get_schema_filtered(table_name="student")
    print(student_schema)