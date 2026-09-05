import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


st.set_page_config(page_title="Hackathon Ready 🚀", page_icon="🚀")

st.title("Hackathon Ready 🚀")

message = st.text_input("请输入内容")

if st.button("提交"):
    if not message.strip():
        st.warning("请输入内容后再提交。")
    elif not os.getenv("OPENAI_API_KEY"):
        st.error("未检测到 OPENAI_API_KEY，请先在项目根目录的 .env 文件中填写。")
    else:
        st.write(f"你刚才说：{message}")

        try:
            client = OpenAI()
            with st.spinner("AI 正在回复..."):
                response = client.responses.create(
                    model="gpt-5.6-luna",
                    input=message,
                )

            st.subheader("AI 回复")
            st.write(response.output_text)
        except Exception:
            st.error("调用 OpenAI API 失败，请检查 API Key、账户权限和网络连接。")
