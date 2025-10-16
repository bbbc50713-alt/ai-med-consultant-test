import json
import os
from qianfan_client import get_chat_completion
from knowledge_base import KnowledgeBase

# 知识库实例在模块加载时初始化一次
db_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
kb = KnowledgeBase(persist_directory=db_directory)

#

# Prompt 模板，用于信息抽取 
INFO_EXTRACTION_PROMPT = """
你是一个严谨的医美顾问信息抽取助手。
根据下面的用户与AI的对话历史，提取用户的核心需求信息。
你必须严格按照以下JSON格式返回，如果某项信息在对话中未明确提及，则其值必须为 null。

输出格式:
{{
  "age": <int, 年龄，例如 26>,
  "budget": "<string, 价格区间，例如 '1000-3000'>",
  "area": "<string, 目标身体部位，例如 '面部'>",
  "keywords": ["<string, 用户的具体需求，例如 '瘦脸', '除皱'>"]
}}

---
对话历史:
{history}
---

请严格根据以上对话历史进行抽取，不要猜测，并直接输出JSON对象。
"""

# Prompt 
RECOMMENDATION_PROMPT = """
你是一位顶级的医美顾问，专业、亲切且有说服力 、且抓住大众心理学中的一些常识。
使得尽最大的能力从对话中,去抓住大众的心理需求,为用户提供个性化的产品推荐。
你的任务是根据用户的个人信息和我们提供的相关产品资料，为用户生成一条专业且个性化的产品推荐。

**你的输出必须严格遵循以下JSON格式:**
{{
  "name": "<string, 推荐的产品名称>",
  "price": <float, 产品的价格>,
  "reason": "<string, 推荐理由。这条理由必须听起来非常专业和有同理心，要结合用户的需求（关键词、预算等）和产品的特点来写，解释为什么这个产品适合TA。>"
}}

---
【用户信息】
{user_info}
---
【供你参考的相关产品资料】
{products_context}
---

请根据以上信息，为用户生成推荐。直接输出JSON对象。
"""

#


def extract_user_info(history_str: str) -> dict:
    """使用LLM从对话历史中抽取结构化的用户信息。"""
    prompt = INFO_EXTRACTION_PROMPT.format(history=history_str)
    response_str = get_chat_completion([{"role": "user", "content": prompt}])
    
    try:
        # 清理可能的代码块标记
        if response_str.startswith("```json"):
            response_str = response_str[7:-4].strip()
        return json.loads(response_str)
    except (json.JSONDecodeError, TypeError):
        print(f"信息抽取失败，LLM返回格式错误: {response_str}")
        return {} # 返回空字典表示解析失败

def generate_recommendation(user_info: dict) -> dict:
    """根据用户信息，检索知识库并生成最终推荐。"""
    # 将用户的关键词和部位组合成一个更丰富的查询语句
    query = f"需求是{','.join(user_info.get('keywords', []))}，部位是{user_info.get('area', '')}"
    
    # 1. 从向量数据库检索最相关的产品
    search_results = kb.search_similar(query, n_results=2)
    if not search_results:
        return {"error": "抱歉，根据您的需求，暂时没有找到合适的产品。"}
    
    products_context = "\n---\n".join([res['content'] for res in search_results])

    # 2. 调用LLM生成最终的推荐理由
    prompt = RECOMMENDATION_PROMPT.format(
        user_info=json.dumps(user_info, ensure_ascii=False),
        products_context=products_context
    )
    response_str = get_chat_completion([{"role": "user", "content": prompt}])
    
    try:
        # 清理可能的代码块标记
        if response_str.startswith("```json"):
            response_str = response_str[7:-4].strip()
        return json.loads(response_str)
    except (json.JSONDecodeError, TypeError):
        print(f"推荐生成失败，LLM返回格式错误: {response_str}")
        return {"error": "推荐内容生成失败，请稍后再试。"}