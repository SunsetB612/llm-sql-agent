from mcp_server import get_schema_filtered, query_data, get_logs
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/query', methods=['POST'])
def http_query():
    data = request.json
    sql = data.get('sql')
    page = data.get('page', 0)
    page_size = data.get('page_size', 50)
    session_id = data.get('session_id', 'default')
    user_message = data.get('user_message', '')
    result = query_data(sql, page, page_size, session_id, user_message)
    return jsonify(result)

@app.route('/schema', methods=['GET'])
def http_schema():
    table = request.args.get('table')
    return jsonify(get_schema_filtered(table))

@app.route('/logs', methods=['GET'])
def http_logs():
    return jsonify(get_logs())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000) 