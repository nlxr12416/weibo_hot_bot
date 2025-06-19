"""
调用大语言模型回复消息
"""
import os
from openai import OpenAI

def get_gpt_reply(prompt):
    """
    调用DeepSeek模型获取回复
    
    Args:
        prompt (str): 用户输入的消息
        
    Returns:
        str: DeepSeek模型的回复
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        error_msg = "错误：环境变量 DEEPSEEK_API_KEY 未设置"
        print(error_msg)
        return error_msg

    try:
        # 初始化 OpenAI 客户端，使用 DeepSeek 的 API 地址
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        # 调用聊天模型
        response = client.chat.completions.create(
            model="deepseek-chat",  # 使用 deepseek-chat 模型
            messages=[
                {"role": "system", "content": "你是一个乐于助人的AI助手。"},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        
        # 返回模型的回复内容
        return response.choices[0].message.content
    except Exception as e:
        error_msg = f"调用DeepSeek API失败: {e}"
        print(error_msg)
        return error_msg 