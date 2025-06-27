import requests
from typing import Optional, Dict
import os
from dataclasses import dataclass

@dataclass
class LLMConfig:
    """LLM配置类"""
    api_key: str 
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-plus"
    temperature: float = 0.1
    max_tokens: int = 2000

class LLMClient:
    """通义千问API客户端，负责自然语言转SQL"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_system_prompt(self, schema_info: Optional[Dict] = None) -> str:
        """构建系统提示词"""
        base_prompt = """你是一个专业的SQL查询生成器。请根据用户的自然语言问题生成对应的SQL查询语句。
            重要要求：
            1.绝对只能使用以下数据库中存在的表和字段，绝对禁止使用未列出的表或字段。
            2. 只返回SQL语句，不要包含任何解释或其他文本
            3. SQL语句要符合MySQL语法规范
            4. 使用适当的WHERE条件、JOIN等语句
            5. 对于模糊查询使用LIKE操作符
            6. 注意SQL注入防护，使用参数化查询思维
            7. 返回的SQL应该是可以直接执行的

            """
        
        if schema_info and isinstance(schema_info, dict) and "tables" in schema_info:
            schema_text = "\n数据库结构信息：\n"
            for table_name, columns in schema_info["tables"].items():
                schema_text += f"\n表名：{table_name}\n字段：\n"
                for col in columns:
                    schema_text += f"  - {col.get('name', '')} ({col.get('type', '')})\n"

            base_prompt += schema_text + "\n"
            base_prompt += """
            示例：
            用户问题：列出所有课程的标题，并按标题和学分排序
            SQL：SELECT `title` FROM `course` ORDER BY `title`, `credits`;

            用户问题：查询所有学生的姓名和年龄
            SQL：SELECT `name`, `age` FROM `student`;

            请严格根据上述表和字段，根据用户问题生成SQL语句：
            """
        
        #print(base_prompt)
        return base_prompt
    
    def _call_api(self, messages: list) -> str:
        """调用通义千问API"""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API调用失败: {str(e)}")
        except KeyError as e:
            raise Exception(f"API响应格式错误: {str(e)}")
    
    def generate_sql(self, question: str, schema_info: Optional[Dict] = None) -> str:
        """
        根据自然语言问题生成SQL语句
        
        Args:
            question: 用户的自然语言问题
            schema_info: 数据库结构信息
            
        Returns:
            生成的SQL语句
        """
        system_prompt = self._build_system_prompt(schema_info)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        sql_response = self._call_api(messages)
        
        # 清理SQL语句（移除可能的markdown标记等）
        sql = self._clean_sql(sql_response)
        
        return sql
    
    def _clean_sql(self, sql_text: str) -> str:
        """清理SQL语句，移除不必要的格式"""
        # 移除markdown代码块标记
        sql_text = sql_text.replace("```sql", "").replace("```", "")
        
        # 移除多余的空白字符
        sql_text = sql_text.strip()
        
        # 确保SQL语句以分号结尾
        if not sql_text.endswith(';'):
            sql_text += ';'
            
        return sql_text

def create_llm_client(api_key: str = None, **kwargs) -> LLMClient:
    """
    创建LLM客户端的便捷函数
    
    Args:
        api_key: API密钥，如果不提供则从环境变量DASHSCOPE_API_KEY获取
        **kwargs: 其他配置参数
        
    Returns:
        LLMClient实例
    """
    if api_key is None:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请提供API密钥或设置环境变量DASHSCOPE_API_KEY")
    
    config = LLMConfig(api_key=api_key, **kwargs)
    return LLMClient(config)

# 向后兼容的函数
def generate_sql(question: str, schema_info: Optional[Dict] = None) -> str:
    """
    兼容原有代码的生成SQL函数
    
    Args:
        question: 用户问题
        schema_info: 数据库结构信息
        
    Returns:
        生成的SQL语句
    """
    client = create_llm_client()
    return client.generate_sql(question, schema_info)

if __name__ == "__main__":
    # 测试代码
    try:
        # 创建客户端
        client = create_llm_client()
        
        # 测试SQL生成
        test_question = "List the name of all courses ordered by their titles and credits"
        sql = client.generate_sql(test_question)
        print(f"问题: {test_question}")
        print(f"生成的SQL: {sql}")
        
    except Exception as e:
        print(f"错误: {e}")
        print("请确保设置了环境变量DASHSCOPE_API_KEY")