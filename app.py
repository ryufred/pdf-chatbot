import streamlit as st
import google.generativeai as genai
import json
import os

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="PDF 문서 챗봇",
    page_icon="📄",
    layout="wide",
)

st.markdown("""
<style>
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
    .doc-badge {
        display: inline-block;
        background: #f0fdf4;
        border: 1px solid #86efac;
        color: #166534;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.78rem;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ── docs 폴더에서 텍스트 로드 ─────────────────────────────────
@st.cache_data
def load_docs():
    docs = {}
    docs_dir = "docs"
    if not os.path.exists(docs_dir):
        return docs
    for fname in os.listdir(docs_dir):
        if fname.endswith(".txt"):
            fpath = os.path.join(docs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                original_name = fname.replace(".txt", ".pdf")
                docs[original_name] = f.read()
    return docs

# ── 세션 초기화 ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── API Key ───────────────────────────────────────────────────
api_key = ""
if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.title("📄 PDF 문서 챗봇")

    if not api_key:
        api_key = st.text_input("🔑 Gemini API Key", type="password",
                                help="aistudio.google.com 에서 무료 발급")
        st.divider()

    docs = load_docs()

    if docs:
        st.markdown(f"**📚 등록된 문서 ({len(docs)}개)**")
        for name in docs:
            st.markdown(f'<span class="doc-badge">📄 {name}</span>',
                        unsafe_allow_html=True)
    else:
        st.warning("등록된 문서가 없습니다.\nadmin 페이지에서 PDF를 등록해 주세요.")

    st.divider()
    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = []
        st.rerun()

    st.caption("무료 한도: 분당 15회 / 하루 1,500회")

# ── 메인 ─────────────────────────────────────────────────────
st.title("📄 문서 기반 챗봇")
st.caption("등록된 PDF 문서를 바탕으로 질문에 답변하고, 출처를 알려드립니다.")

if not docs:
    st.info("📭 등록된 문서가 없습니다. 관리자 페이지에서 PDF를 먼저 등록해 주세요.")
    st.stop()

# 채팅 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citation"):
            st.markdown(
                f'<div class="citation-box">📌 출처<br>{msg["citation"]}</div>',
                unsafe_allow_html=True,
            )

# ── 입력 처리 ─────────────────────────────────────────────────
prompt = st.chat_input("문서에 대해 질문하세요...")

if prompt:
    if not api_key:
        st.warning("⚠️ Gemini API Key를 입력해 주세요.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("문서를 검색 중..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")

                docs_text = ""
                for fname, text in docs.items():
                    truncated = text[:80000]
                    if len(text) > 80000:
                        truncated += "\n...(이하 생략)"
                    docs_text += f"\n\n===== 문서: {fname} =====\n{truncated}"

                full_prompt = f"""당신은 업로드된 문서 전문가입니다.
아래 문서들을 참고해 사용자 질문에 답하세요.
반드시 아래 JSON 형식으로만 응답하세요 (마크다운 코드블록 없이 순수 JSON):

{{
  "found": true 또는 false,
  "answer": "답변 내용 (found=false면 빈 문자열)",
  "citations": [
    {{"file": "파일명.pdf", "page": "페이지 번호 (예: 3페이지)", "excerpt": "해당 부분 핵심 내용 1~2문장"}}
  ]
}}

규칙:
- 문서에 관련 내용이 있으면 found=true, 출처 파일명과 페이지를 포함하세요.
- 문서에 없으면 found=false, citations는 빈 배열로 하세요.
- 여러 파일에서 찾으면 citations에 모두 포함하세요.
- 답변은 한국어로 작성하세요.

{docs_text}

질문: {prompt}"""

                response = model.generate_content(full_prompt)
                raw = response.text.strip()

                try:
                    result = json.loads(raw)
                except json.JSONDecodeError:
                    cleaned = raw.replace("```json", "").replace("```", "").strip()
                    result = json.loads(cleaned)

                if result.get("found"):
                    answer = result.get("answer", "")
                    citations = result.get("citations", [])

                    citation_parts = []
                    for c in citations:
                        fname = c.get("file", "")
                        page = c.get("page", "")
                        excerpt = c.get("excerpt", "")
                        page_str = f" ({page})" if page else ""
                        citation_parts.append(f"<b>{fname}</b>{page_str} — {excerpt}")
                    citation_str = "<br>".join(citation_parts)

                    st.markdown(answer)
                    if citation_str:
                        st.markdown(
                            f'<div class="citation-box">📌 출처<br>{citation_str}</div>',
                            unsafe_allow_html=True,
                        )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "citation": citation_str,
                    })
                else:
                    no_result = "업로드된 문서에서 관련 내용을 찾을 수 없습니다."
                    st.markdown(no_result)
                    st.markdown(
                        '<div class="no-result-box">⚠️ 해당 내용이 문서에 없습니다.</div>',
                        unsafe_allow_html=True,
                    )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": no_result,
                    })

            except Exception as e:
                st.error(f"오류 발생: {e}")
