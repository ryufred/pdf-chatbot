import streamlit as st
import io
import os

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="관리자 - PDF 등록", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
    .registered-card {
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .delete-hint { font-size: 0.78rem; color: #6b7280; }
</style>
""", unsafe_allow_html=True)

# ── 관리자 비밀번호 ───────────────────────────────────────────
ADMIN_PW = st.secrets.get("ADMIN_PASSWORD", "admin1234") if hasattr(st, "secrets") else "admin1234"

if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

if not st.session_state.admin_auth:
    st.title("⚙️ 관리자 로그인")
    pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pw == ADMIN_PW:
            st.session_state.admin_auth = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# ── 텍스트 추출 함수 ──────────────────────────────────────────
def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[페이지 {i+1}]\n{text.strip()}")
    return "\n\n".join(pages)

DOCS_DIR = "docs"
os.makedirs(DOCS_DIR, exist_ok=True)

# ── 관리자 UI ─────────────────────────────────────────────────
st.title("⚙️ 관리자 — PDF 문서 등록")
st.caption("여기서 등록한 PDF는 사용자 챗봇에서 새로고침 후에도 유지됩니다.")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📤 PDF 업로드")
    uploaded = st.file_uploader("PDF 파일 선택 (여러 개 가능)", type=["pdf"],
                                 accept_multiple_files=True)

    if uploaded:
        if st.button("✅ 등록하기", type="primary"):
            progress = st.progress(0)
            for i, f in enumerate(uploaded):
                with st.spinner(f"📖 {f.name} 처리 중..."):
                    text = extract_text(f.read())
                    save_name = f.name.replace(".pdf", ".txt")
                    save_path = os.path.join(DOCS_DIR, save_name)
                    with open(save_path, "w", encoding="utf-8") as out:
                        out.write(text)
                progress.progress((i + 1) / len(uploaded))
            st.success(f"✅ {len(uploaded)}개 파일 등록 완료!")
            st.cache_data.clear()   # app.py 캐시 초기화
            st.rerun()

with col2:
    st.subheader("📚 등록된 문서")
    files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")]

    if not files:
        st.info("등록된 문서가 없습니다.")
    else:
        for fname in sorted(files):
            fpath = os.path.join(DOCS_DIR, fname)
            size = os.path.getsize(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                char_count = len(f.read())
            original = fname.replace(".txt", ".pdf")

            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(
                        f'<div class="registered-card">'
                        f'📄 <b>{original}</b><br>'
                        f'<span class="delete-hint">{char_count:,}자 추출됨 | {size/1024:.1f} KB</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("🗑️", key=f"del_{fname}", help=f"{original} 삭제"):
                        os.remove(fpath)
                        st.cache_data.clear()
                        st.rerun()

st.divider()
if st.button("🚪 로그아웃"):
    st.session_state.admin_auth = False
    st.rerun()
