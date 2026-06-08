import streamlit as st
import google.generativeai as genai
import json
import io
import os

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

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
        padding: 3px 12px;
        font-size: 0.8rem;
        margin: 2px 0;
    }
    .registered-card {
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ── 설정 ─────────────────────────────────────────────────────
DOCS_DIR = "docs"
os.makedirs(DOCS_DIR, exist_ok=True)

def get_secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except:
        return default

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "admin1234")

# ── PDF 텍스트 추출 ───────────────────────────────────────────
def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[페이지 {i+1}]\n{text.strip()}")
    return "\n\n".join(pages)

# ── 등록된 문서 로드 ──────────────────────────────────────────
@st.cache_data
def load_docs():
    docs = {}
    if not os.path.exists(DOCS_DIR):
        return docs
    for fname in sorted(os.listdir(DOCS_DIR)):
        if fname.endswith(".txt"):
            fpath = os.path.join(DOCS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                docs[fname.replace(".txt", ".pdf")] = f.read()
    return docs

# ── 세션 초기화 ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

# ── URL 파라미터로 모드 결정 ──────────────────────────────────
params = st.query_params
is_admin_page = params.get("mode") == "admin"

# ════════════════════════════════════════════════════════════
# 관리자 화면
# ════════════════════════════════════════════════════════════
if is_admin_page:
    st.title("⚙️ 관리자 — PDF 문서 등록")

    # 로그인
    if not st.session_state.admin_auth:
        st.subheader("🔒 관리자 로그인")
        pw = st.text_input("비밀번호", type="password")
        if st.button("로그인", type="primary"):
            if pw == ADMIN_PASSWORD:
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
        st.stop()

    st.caption("여기서 등록한 PDF는 사용자 챗봇에 바로 반영됩니다.")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("📤 PDF 업로드")
        uploaded = st.file_uploader(
            "PDF 파일 선택 (여러 개 가능)",
            type=["pdf"],
            accept_multiple_files=True,
        )
        if uploaded:
            if st.button("✅ 등록하기", type="primary"):
                progress = st.progress(0)
                for i, f in enumerate(uploaded):
                    with st.spinner(f"📖 {f.name} 처리 중..."):
                        text = extract_text(f.read())
                        save_path = os.path.join(DOCS_DIR, f.name.replace(".pdf", ".txt"))
                        with open(save_path, "w", encoding="utf-8") as out:
                            out.write(text)
                    progress.progress((i + 1) / len(uploaded))
                st.success(f"✅ {len(uploaded)}개 파일 등록 완료!")
                st.cache_data.clear()
                st.rerun()

    with col2:
        st.subheader("📚 등록된 문서")
        files = sorted([f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")])
        if not files:
            st.info("등록된 문서가 없습니다.")
        else:
            for fname in files:
                fpath = os.path.join(DOCS_DIR, fname)
                size_kb = os.path.getsize(fpath) / 1024
                with open(fpath, "r", encoding="utf-8") as f:
                    char_count = len(f.read())
                original = fname.replace(".txt", ".pdf")
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f'<div class="registered-card">'
                        f'📄 <b>{original}</b><br>'
                        f'<span style="color:#6b7280;font-size:0.78rem">'
                        f'{char_count:,}자 추출 | {size_kb:.1f} KB</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("🗑️", key=f"del_{fname}"):
                        os.remove(fpath)
                        st.cache_data.clear()
                        st.rerun()

    st.divider()
    if st.button("🚪 로그아웃"):
        st.session_state.admin_auth = False
        st.rerun()

# ════════════════════════════════════════════════════════════
# 사용자 화면 (챗봇)
# ════════════════════════════════════════════════════════════
else:
    docs = load_docs()

    # 사이드바
    with st.sidebar:
        st.title("📄 PDF 문서 챗봇")

        api_key = GEMINI_API_KEY
        if not api_key:
            api_key = st.text_input("🔑 Gemini API Key", type="password",
                                    help="aistudio.google.com 에서 무료 발급")
        st.divider()

        if docs:
            st.markdown(f"**📚 등록된 문서 ({len(docs)}개)**")
            for name in docs:
                st.markdown(f'<div class="doc-badge">📄 {name}</div>',
                            unsafe_allow_html=True)
        else:
            st.warning("등록된 문서가 없습니다.")

        st.divider()
        if st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()
        st.caption("무료 한도: 분당 15회 / 하루 1,500회")

    # 메인
    st.title("📄 문서 기반 챗봇")
    st.caption("등록된 PDF 문서를 바탕으로 질문에 답변하고, 출처를 알려드립니다.")

    if not docs:
        st.info("📭 등록된 문서가 없습니다. 관리자가 PDF를 등록하면 바로 사용할 수 있어요.")
        st.stop()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citation"):
                st.markdown(
                    f'<div class="citation-box">📌 출처<br>{msg["citation"]}</div>',
                    unsafe_allow_html=True,
                )

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
                    model = genai.GenerativeModel("gemini-1.5-flash-latest")

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
