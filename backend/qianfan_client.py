# backend/qianfan_client.py
from openai import OpenAI
import os

# 建议从环境变量读取，更安全    
QIANFAN_API_KEY = os.getenv("QIANFAN_API_KEY", "bce-v3/ALTAK-azeEaKzwbSAZbEmeMcBBa/b78c8d2a073a0f3a8a541c04c2e1e60573b53bd8") 
QIANFAN_BASE_URL = os.getenv("QIANFAN_BASE_URL", "https://qianfan.baidubce.com/v2")

client = OpenAI(
    base_url=QIANFAN_BASE_URL,
    api_key=QIANFAN_API_KEY
)

def get_chat_completion(messages: list, model="deepseek-v3"):
    """
    调用千帆大模型获取聊天回复。

    Args:
        messages (list): 对话历史，格式为 [{"role": "user", "content": "..."}]。
        model (str): 要调用的模型名称。

    Returns:
        str: 模型返回的文本回复。
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7, # 稍微降低一点，让输出更稳定
            top_p=0.8,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"调用千帆模型时出错: {e}")
        return "抱歉，AI服务当前似乎有些问题，请稍后再试。"