import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mcp_server import get_schema_filtered

def print_schema(schema):
    print(f"数据库: {schema.get('database', '')}")
    tables = schema.get('tables', {})
    if not tables:
        print("无表结构信息。")
        return
    for tname, columns in tables.items():
        print(f"表: {tname}")
        if not columns:
            print("  (无字段)")
            continue
        # 设置每列的宽度
        header = ["字段名", "类型", "允许空", "主键", "默认值", "额外信息"]
        widths = [12, 20, 8, 6, 12, 12]
        # 打印表头
        print("  " + "  ".join(f"{h:<{w}}" for h, w in zip(header, widths)))
        # 打印每一行
        for col in columns:
            row = [
                f"{col['name']:<{widths[0]}}",
                f"{col['type']:<{widths[1]}}",
                f"{col['null']:<{widths[2]}}",
                f"{col['key']:<{widths[3]}}",
                f"{str(col['default']):<{widths[4]}}",
                f"{col['extra']:<{widths[5]}}"
            ]
            print("  " + "  ".join(row))
        print()

if __name__ == "__main__":
    print("=== 获取所有表结构 ===")
    all_schema = get_schema_filtered()
    print_schema(all_schema)

    print("\n=== 获取 student 表结构 ===")
    student_schema = get_schema_filtered(table_name="student")
    print_schema(student_schema)