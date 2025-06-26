import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import json
import time
import uuid
from datetime import datetime
import re
from typing import Dict, Any, List, Optional
import traceback

import dotenv
dotenv.load_dotenv()

# 导入现有的模块
try:
    from src.llm_client import create_llm_client
    from src.database_handler import DatabaseHandler, DatabaseConfig
    from src.mcp_server import (
        get_or_create_session, 
        cleanup_expired_sessions,
        clear_conversation_context,
        get_conversation_context
    )
    MODULES_LOADED = True
except ImportError as e:
    st.error(f"模块导入失败: {str(e)}")
    MODULES_LOADED = False

# 设置页面配置
st.set_page_config(
    page_title="智能数据库查询可视化系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        text-align: center;
        margin: 0;
    }
    .query-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .result-box {
        background: #f1f8ff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c6e2ff;
        margin: 1rem 0;
    }
    .error-box {
        background: #fff5f5;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #fed7d7;
        margin: 1rem 0;
    }
    .success-box {
        background: #f0fff4;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #9ae6b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitNLQuerySystem:
    """Streamlit版本的自然语言查询系统"""
    
    def __init__(self):
        self.db_config = DatabaseConfig()
        self.session_id = self._get_or_create_session_id()
        
    def _get_or_create_session_id(self):
        """获取或创建会话ID"""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = f"streamlit_session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        return st.session_state.session_id
    
    async def query_database(self, question: str, use_schema: bool = True) -> Dict[str, Any]:
        """执行数据库查询"""
        try:
            if not MODULES_LOADED:
                raise Exception("必要的模块未正确加载")
            # 创建LLM客户端
            llm_client = create_llm_client()
            # 创建数据库处理器
            async with DatabaseHandler(self.db_config) as db_handler:
                # 获取数据库结构
                schema_info = None
                if use_schema:
                    schema_info = await db_handler.get_schema()
                # 生成SQL
                sql = llm_client.generate_sql(question, schema_info)
                # 执行查询
                query_result = await db_handler.execute_sql(sql, page=0, page_size=1000000)
                return {
                    "question": question,
                    "sql": sql,
                    "query_result": query_result,
                    "schema_used": schema_info is not None,
                    "session_id": self.session_id
                }
        except Exception as e:
            st.error(f"查询失败: {str(e)}\n{traceback.format_exc()}")
            return {
                "question": question,
                "sql": "",
                "query_result": {
                    "success": False,
                    "error": str(e),
                    "results": None,
                    "rowcount": 0
                },
                "schema_used": False,
                "session_id": self.session_id
            }

def detect_chart_type(df: pd.DataFrame, columns: List[str]) -> str:
    """根据数据类型自动检测合适的图表类型"""
    if df.empty or len(columns) < 1:
        return "table"
    
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    
    # 时间序列数据
    if len(datetime_cols) >= 1 and len(numeric_cols) >= 1:
        return "line"
    
    # 一个分类变量 + 一个数值变量
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        unique_values = df[categorical_cols[0]].nunique()
        if unique_values <= 10:
            return "bar"
        elif unique_values <= 50:
            return "histogram"
    
    # 两个数值变量
    if len(numeric_cols) >= 2:
        return "scatter"
    
    # 单个数值变量
    if len(numeric_cols) == 1:
        return "histogram"
    
    return "table"

def create_visualization(df: pd.DataFrame, chart_type: str, title: str = "查询结果可视化") -> go.Figure:
    """创建可视化图表"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="没有数据可显示", showarrow=False, font=dict(size=20))
        return fig
    
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    
    try:
        if chart_type == "bar" and len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0], title=title)
            
        elif chart_type == "line" and len(numeric_cols) >= 1:
            if len(datetime_cols) >= 1:
                fig = px.line(df, x=datetime_cols[0], y=numeric_cols[0], title=title)
            else:
                fig = px.line(df, y=numeric_cols[0], title=title)
                
        elif chart_type == "scatter" and len(numeric_cols) >= 2:
            color_col = categorical_cols[0] if categorical_cols else None
            fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], 
                           color=color_col, title=title)
            
        elif chart_type == "pie" and len(categorical_cols) >= 1:
            if len(numeric_cols) >= 1:
                fig = px.pie(df, names=categorical_cols[0], values=numeric_cols[0], title=title)
            else:
                value_counts = df[categorical_cols[0]].value_counts()
                fig = px.pie(values=value_counts.values, names=value_counts.index, title=title)
                
        elif chart_type == "histogram" and len(numeric_cols) >= 1:
            fig = px.histogram(df, x=numeric_cols[0], title=title)
            
        elif chart_type == "box" and len(numeric_cols) >= 1:
            y_col = numeric_cols[0]
            x_col = categorical_cols[0] if categorical_cols else None
            fig = px.box(df, x=x_col, y=y_col, title=title)
            
        else:
            # 默认创建一个简单的表格可视化
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(df.columns),
                           fill_color='paleturquoise',
                           align='left'),
                cells=dict(values=[df[col] for col in df.columns],
                          fill_color='lavender',
                          align='left'))
            ])
            fig.update_layout(title=title)
            
        # 统一设置图表样式
        fig.update_layout(
            height=500,
            showlegend=True,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        return fig
        
    except Exception as e:
        # 如果创建图表失败，返回错误信息
        fig = go.Figure()
        fig.add_annotation(text=f"图表创建失败: {str(e)}", showarrow=False, font=dict(size=16))
        return fig

def display_query_history():
    """显示查询历史"""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    if st.session_state.query_history:
        st.subheader("📚 查询历史")
        for i, history_item in enumerate(reversed(st.session_state.query_history[-10:])):  # 显示最近10条
            with st.expander(f"查询 {len(st.session_state.query_history)-i}: {history_item['question'][:50]}..."):
                st.markdown(f"**问题:** {history_item['question']}")
                st.markdown(f"**SQL:** `{history_item['sql']}`")
                st.markdown(f"**时间:** {history_item['timestamp']}")
                if history_item['success']:
                    st.success(f"✅ 成功 - 返回 {history_item['rowcount']} 条记录")
                else:
                    st.error(f"❌ 失败 - {history_item['error']}")

def main():
    """主函数"""
    if not MODULES_LOADED:
        st.error("❌ 系统初始化失败，请检查依赖模块")
        st.stop()
    # 页面标题
    st.markdown("""
    <div class="main-header">
        <h1>🔍 智能数据库查询可视化系统</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化系统
    system = StreamlitNLQuerySystem()
    
    # 主要内容区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 自然语言查询")
        # 查询输入
        question = st.text_area(
            "请输入您的问题:",
            height=100,
            placeholder="例如: 显示所有学生的姓名和年龄\n查询课程表中学分最高的前5门课程\n统计各个年级的学生人数",
            help="用自然语言描述您想要查询的内容"
        )
        # 查询按钮
        if st.button("🔍 执行查询", type="primary"):
            if question.strip():
                with st.spinner("正在处理您的查询..."):
                    # 执行查询
                    result = asyncio.run(system.query_database(question))
                    # 保存到历史记录
                    if 'query_history' not in st.session_state:
                        st.session_state.query_history = []
                    history_item = {
                        'question': question,
                        'sql': result['sql'],
                        'success': result['query_result']['success'],
                        'rowcount': result['query_result']['rowcount'],
                        'error': result['query_result'].get('error', ''),
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.query_history.append(history_item)
                    # 缓存本次查询的 DataFrame
                    if result['query_result']['success']:
                        results = result['query_result']['results']
                        st.session_state['last_query_df'] = pd.DataFrame(results) if results else pd.DataFrame()
                    else:
                        st.session_state['last_query_df'] = None
                    # 缓存查询结果区块内容
                    st.session_state['last_query_result'] = result
            else:
                st.warning("请输入查询问题")

        # 查询按钮外部，始终显示查询结果区块
        last_result = st.session_state.get('last_query_result', None)
        if last_result is not None:
            st.markdown("### 📋 查询结果")
            with st.expander("📝 生成的SQL语句", expanded=True):
                st.code(last_result['sql'], language='sql')
            if last_result['query_result']['success']:
                rowcount = last_result['query_result']['rowcount']
                st.markdown(f"""
                <div class="success-box">
                    ✅ <strong>查询成功!</strong> 返回 {rowcount} 条记录
                </div>
                """, unsafe_allow_html=True)
            else:
                error_msg = last_result['query_result'].get('error', '未知错误')
                st.markdown(f"""
                <div class="error-box">
                    ❌ <strong>查询失败:</strong> {error_msg}
                </div>
                """, unsafe_allow_html=True)

        # 查询按钮外部，始终显示分页表格
        df_cache = st.session_state.get('last_query_df', None)
        if df_cache is not None and not df_cache.empty:
            st.subheader("📊 数据表")
            page_size = 50
            total_rows = len(df_cache)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1
            page = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1, key="page_number")
            start = (page - 1) * page_size
            end = start + page_size
            page_df = df_cache.iloc[start:end].copy()
            page_df.index = range(start + 1, min(end, total_rows) + 1)
            st.dataframe(page_df, use_container_width=True)
            st.info(f"当前第 {page}/{total_pages} 页，每页 {page_size} 条，共 {total_rows} 条")
        else:
            st.info("无数据可显示")

    with col2:
        # 显示查询历史
        display_query_history()

if __name__ == "__main__":
    main()