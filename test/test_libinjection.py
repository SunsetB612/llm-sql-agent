import libinjection

def is_sql_injection(sql: str) -> bool:
    return libinjection.is_sql_injection(sql)["is_sqli"]   # 只取布尔位

# 测试
payload = "1' OR 1=1 -- "
print(is_sql_injection(payload))      # True