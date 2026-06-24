import streamlit as st
from ingest import register_pdf
from supabase import create_client
import os
from config import PDF_DIR, SUPABASE_URL, SUPABASE_KEY
from dotenv import load_dotenv

load_dotenv()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="관리자 페이지",
    page_icon="⚙️",
    layout="centered"
)

st.title("⚙️ 관리자 페이지")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if not st.session_state.is_admin:
    st.subheader("🔒 관리자 로그인")
    pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pw == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다")
else:
    st.success("관리자로 로그인됨")
    if st.button("로그아웃"):
        st.session_state.is_admin = False
        st.rerun()

    st.divider()

    # PDF 업로드
    st.subheader("📤 PDF 업로드")
    uploaded_files = st.file_uploader(
        "PDF 파일을 선택하세요",
        type="pdf",
        accept_multiple_files=True
    )
    if uploaded_files:
        if st.button("업로드 및 등록"):
            os.makedirs(PDF_DIR, exist_ok=True)
            for uploaded_file in uploaded_files:
                save_path = os.path.join(PDF_DIR, uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                with st.spinner(f"{uploaded_file.name} 등록 중..."):
                    try:
                        register_pdf(save_path)
                        st.success(f"✅ {uploaded_file.name} 등록 완료!")
                    except Exception as e:
                        st.error(f"❌ {uploaded_file.name} 오류: {e}")

    st.divider()

    # 등록된 파일 목록
    st.subheader("📋 등록된 파일 목록")
    result = supabase.table("documents").select("filename").execute()
    if result.data:
        filenames = list(set([r["filename"] for r in result.data]))
        filenames.sort()
        for fname in filenames:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📄 {fname}")
            with col2:
                if st.button("삭제", key=f"del_{fname}"):
                    supabase.table("documents").delete().eq("filename", fname).execute()
                    pdf_path = os.path.join(PDF_DIR, fname)
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    st.success(f"{fname} 삭제 완료!")
                    st.rerun()
    else:
        st.info("등록된 파일이 없습니다")