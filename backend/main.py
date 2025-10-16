# backend/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import json

from logic import extract_user_info, generate_recommendation
from qianfan_client import get_chat_completion

app = FastAPI()

class ChatRequest(BaseModel):
    history: List[Dict[str, str]] # e.g., [{"role": "user", "content": "你好"}]

class ChatResponse(BaseModel):
    response: str
    is_recommendation: bool = False
    data: Dict = None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    history = request.history
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    # 1. 尝试抽取用户信息
    user_info = extract_user_info(history_str)

    # 2. 检查关键信息是否完整
    required_keys = ["age", "budget", "area", "keywords"]
    is_info_complete = all(user_info.get(key) for key in required_keys)

    if is_info_complete:
        # 3. 生成推荐
        recommendation = generate_recommendation(user_info)
        response_str = json.dumps(recommendation, ensure_ascii=False)
        return ChatResponse(response=response_str, is_recommendation=True, data=recommendation)
    else:
        # 4. 如果信息不完整，继续引导对话
        system_prompt = "你是一个专业的医美顾问，你的任务是自然地引导用户说出他们的年龄、预算、想改善的部位和具体需求（如瘦脸、除皱），以便为他们推荐项目。"
        messages = [{"role": "system", "content": system_prompt}] + history
        ai_response = get_chat_completion(messages)
        return ChatResponse(response=ai_response, is_recommendation=False)