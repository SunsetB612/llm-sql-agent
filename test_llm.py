from src.llm_client import generate_sql

question = "List the titles of all course ordered by their titles and credits. "
sql = generate_sql(question)
print("生成的 SQL：")
print(sql)
