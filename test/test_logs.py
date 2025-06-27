import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mcp_server import get_logs

if __name__ == "__main__":
    logs_result = get_logs()
    print(f"日志总数: {logs_result.get('count', 0)}")
    logs = logs_result.get('logs', [])
    if not logs:
        print("无日志记录。")
    else:
        print("日志详情:")
        for i, log in enumerate(logs, 1):
            print(f"[{i}] {log.get('timestamp', '')} [{log.get('level', '')}] {log.get('message', '')}") 