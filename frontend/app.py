import streamlit as st
import requests
import json

# --- 页面配置 ---
st.set_page_config(page_title="AI 医美顾问", page_icon="👩‍⚕️", layout="centered")

# --- 页面标题和介绍 ---
st.title("AI 医美顾问 👩‍⚕️")
st.markdown(
    "你好！我是一位专业的AI医美顾问。告诉我你的美丽困扰，"
    "例如 **“我今年26岁，预算3000左右，想让脸瘦一点”**，我会尽力为你提供帮助。"
)

# --- 后端API地址 ---
BACKEND_URL = "http://127.0.0.1:8000/chat"

# --- 初始化会话状态 ---
if "messages" not in st.session_state:
    # 初始欢迎语
    st.session_state.messages = [{"role": "assistant", "content": "您好！请问有什么可以帮助您的吗？"}]

# --- 显示历史聊天记录 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # 特殊处理推荐消息的显示
        if message.get("is_recommendation"):
            rec_data = message.get("data")
            if rec_data and isinstance(rec_data, dict):
                st.markdown(f"好的，根据您的需求，我为您推荐以下项目：")
                st.markdown(f"#### ✨ **{rec_data.get('name', 'N/A')}**")
                st.success(f"**参考价格**: ¥ {rec_data.get('price', 'N/A')}")
                st.info(f"**推荐理由**: {rec_data.get('reason', 'N/A')}")
            else:
                st.markdown("收到了推荐信息，但格式似乎有误。")
        else:
            st.markdown(message["content"])

# --- 接收用户输入 ---
if prompt := st.chat_input("请输入您的年龄、预算和需求..."):
    # 1. 将用户输入添加到消息历史中并显示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用后端API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("AI 正在思考中...")

        try:
            # 准备发送到后端的历史记录
            history_for_api = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
                if "is_recommendation" not in m # 不将格式化的推荐消息发回
            ]
            
            api_response = requests.post(
                BACKEND_URL, 
                json={"history": history_for_api},
                timeout=60 # 设置60秒超时
            )
            api_response.raise_for_status()
            
            response_data = api_response.json()
            
            # 准备要显示和存储的AI回复
            assistant_message = {
                "role": "assistant",
                "content": response_data["response"],
                "is_recommendation": response_data.get("is_recommendation", False),
                "data": response_data.get("data")
            }

            # 3. 将AI的回复添加到消息历史
            st.session_state.messages.append(assistant_message)
            
            # 4. 更新占位符中的内容为最终回复
            # 根据是否是推荐，选择不同的显示方式
            if assistant_message.get("is_recommendation"):
                rec_data = assistant_message.get("data")
                message_placeholder.markdown(f"好的，根据您的需求，我为您推荐以下项目：")
                st.markdown(f"#### ✨ **{rec_data.get('name', 'N/A')}**")
                st.success(f"**参考价格**: ¥ {rec_data.get('price', 'N/A')}")
                st.info(f"**推荐理由**: {rec_data.get('reason', 'N/A')}")
            else:
                 message_placeholder.markdown(assistant_message["content"])

        except requests.exceptions.RequestException as e:
            error_message = f"网络请求失败，无法连接到AI服务。请确保后端正在运行。错误: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})