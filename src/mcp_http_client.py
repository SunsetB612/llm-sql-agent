import requests

MCP_SERVER_URL = "http://localhost:8000"

def mcp_query(sql, page=0, page_size=50, session_id="default", user_message=""):
    url = f"{MCP_SERVER_URL}/query"
    payload = {
        "sql": sql,
        "page": page,
        "page_size": page_size,
        "session_id": session_id,
        "user_message": user_message
    }
    resp = requests.post(url, json=payload)
    return resp.json()

def mcp_schema(table=None):
    url = f"{MCP_SERVER_URL}/schema"
    params = {"table": table} if table else {}
    resp = requests.get(url, params=params)
    return resp.json()

def mcp_logs():
    url = f"{MCP_SERVER_URL}/logs"
    resp = requests.get(url)
    return resp.json() 