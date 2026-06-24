import os
from dotenv import load_dotenv

load_dotenv()

# API 키
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 설정값
CHUNK_SIZE = 500        # 텍스트 자르는 크기
CHUNK_OVERLAP = 50      # 청크 간 겹치는 글자 수 (문맥 유지용)
TOP_K = 5               # 질문 시 검색할 청크 개수
EMBED_MODEL = "jhgan/ko-sroberta-multitask"  # 한국어 임베딩 모델

# PDF 폴더 경로
PDF_DIR = "./pdfs"      # PDF