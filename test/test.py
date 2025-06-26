import os, sys, inspect, libinjection

# ★ 根据 test.py 所在目录，把上层 ../src 加入搜索路径
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../src")   # ← 按你的目录结构改
    )
)

import mcp_server

print("mcp_server.is_sql_injection 定义于:", mcp_server.is_sql_injection.__module__)
print("源文件:", inspect.getfile(mcp_server))
print("\n函数源码 ↓↓↓")
print(inspect.getsource(mcp_server.is_sql_injection))

print("\nlibinjection 检测 `SELECT title FROM course;` =",
      libinjection.is_sql_injection("SELECT title FROM course;")["is_sqli"])
