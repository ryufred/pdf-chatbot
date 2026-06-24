import streamlit as st
from query import ask
import os
import time
from config import PDF_DIR

st.set_page_config(
    page_title="지식뱅크 검색 봇",
    page_icon="🏦",
    layout="centered"
)

st.title("🏦 지식뱅크 검색 봇")
st.caption("PDF 자료 기반으로 질문에 답변합니다")

if "messages" not in st.session_state:
    st.session_state.messages = []

def show_sources(sources, key_prefix):
    with st.expander("📄 출처 파일"):
        for s in sources:
            st.write(f"• {s}")
            pdf_path = os.path.join(PDF_DIR, s)
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {s} 다운로드",
                        data=f,
                        file_name=s,
                        mime="application/pdf",
                        key=f"{key_prefix}_{s}_{time.time_ns()}"
                    )

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "sources" in msg and msg["sources"]:
            show_sources(msg["sources"], f"hist_{i}")

if question := st.chat_input("질문을 입력하세요..."):
    with st.chat_message("user"):
        st.write(question)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        with st.spinner("검색 중..."):
            answer, sources = ask(question)
        st.write(answer)
        if sources:
            show_sources(sources, f"new_{len(st.session_state.messages)}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources
    })