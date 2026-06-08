import streamlit as st
import anthropic
import base64
import json
from pathlib import Path

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="PDF 문서 챗봇",
    page_icon="📄",
    layout="wide",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #f8f9fa; }
    .stChatMessage { border-radius: 12px; margin-bottom: 8px; }
    .citation-box {
        background: #eef2ff;
        border-left: 4px solid #6366f1;
        padding: 10px 14px;
        border-radius: 6px;
        margin-top: 8px;
        font-size: 0.85rem;
        color: #3730a3;
    }
    .no-result-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 10px 14px;
        border-radius: 6px;
        margin-top: 8px;
        font-size: 0.85rem;
        color: #92400e;
    }
</style>
""", unsafe_allow_html=True)

# ── 세션 초기화 ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = {}   # {filename: base64_str}

# ── 사이드바: PDF 업로드 ──────────────────────────────────────
with st.sidebar:
    st.header("📂 문서 업로드")
    st.caption("PDF 파일을 업로드하면 내용을 분석해 답변합니다.")

    api_key = st.text_input("🔑 Anthropic API Key", type="password",
                             help="https://console.anthropic.com 에서 발급")

    uploaded_files = st.file_uploader(
        "PDF 파일 선택 (여러 개 가능)",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.pdf_data:
                st.session_state.pdf_data[f.name] = base64.standard_b64encode(f.read()).decode("utf-8")
        st.success(f"✅ {len(st.session_state.pdf_data)}개 파일 로드됨")
        for name in st.session_state.pdf_data:
            st.markdown(f"- 📄 `{name}`")

    if st.button("🗑️ 문서 초기화"):
        st.session_state.pdf_data = {}
        st.session_state.messages = []
        st.rerun()

# ── 메인 UI ───────────────────────────────────────────────────
st.title("📄 PDF 문서 챗봇")
st.caption("업로드한 PDF 문서 내용을 바탕으로 질문에 답변하고, 출처를 알려드립니다.")

# 채팅 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citation"):
            st.markdown(f'<div class="citation-box">📌 {msg["citation"]}</div>',
                        unsafe_allow_html=True)

# ── 입력 처리 ─────────────────────────────────────────────────
prompt = st.chat_input("문서에 대해 질문하세요...")

if prompt:
    if not api_key:
        st.warning("⚠️ 사이드바에 Anthropic API Key를 입력해 주세요.")
        st.stop()
    if not st.session_state.pdf_data:
        st.warning("⚠️ 사이드바에서 PDF 파일을 먼저 업로드해 주세요.")
        st.stop()

    # 사용자 메시지 저장 & 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Claude API 호출
    with st.chat_message("assistant"):
        with st.spinner("문서를 검색 중..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)

                # 시스템 프롬프트
                system_prompt = """당신은 업로드된 PDF 문서 전문가입니다.
사용자의 질문에 반드시 아래 JSON 형식으로만 답변하세요 (마크다운 코드블록 없이 순수 JSON):

{
  "found": true 또는 false,
  "answer": "답변 내용 (found=false면 빈 문자열)",
  "citations": [
    {"file": "파일명.pdf", "excerpt": "인용된 내용 요약 (1~2문장)"}
  ]
}

규칙:
- 문서에 관련 내용이 있으면 found=true, 답변과 출처 파일명을 포함하세요.
- 문서에 없으면 found=false, citations는 빈 배열로 하세요.
- 여러 파일에서 내용을 찾으면 citations에 모두 포함하세요.
- 답변은 한국어로 작성하세요."""

                # 메시지 구성: 모든 PDF를 document로 첨부
                content = []
                for fname, b64 in st.session_state.pdf_data.items():
                    content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": b64,
                        },
                        "title": fname,
                    })
                content.append({"type": "text", "text": prompt})

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": content}],
                )

                raw = response.content[0].text.strip()
                # JSON 파싱
                try:
                    result = json.loads(raw)
                except json.JSONDecodeError:
                    # 혹시 코드블록이 포함된 경우 제거 후 재시도
                    cleaned = raw.replace("```json", "").replace("```", "").strip()
                    result = json.loads(cleaned)

                if result.get("found"):
                    answer = result.get("answer", "")
                    citations = result.get("citations", [])

                    # 출처 문자열 생성
                    citation_parts = []
                    for c in citations:
                        fname = c.get("file", "")
                        excerpt = c.get("excerpt", "")
                        citation_parts.append(f"**{fname}** — {excerpt}")
                    citation_str = "<br>".join(citation_parts) if citation_parts else ""

                    st.markdown(answer)
                    if citation_str:
                        st.markdown(f'<div class="citation-box">📌 출처<br>{citation_str}</div>',
                                    unsafe_allow_html=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "citation": citation_str,
                    })
                else:
                    no_result = "업로드된 문서에서 관련 내용을 찾을 수 없습니다."
                    st.markdown(no_result)
                    st.markdown('<div class="no-result-box">⚠️ 해당 내용이 문서에 없습니다.</div>',
                                unsafe_allow_html=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": no_result,
                    })

            except Exception as e:
                st.error(f"오류 발생: {e}")
