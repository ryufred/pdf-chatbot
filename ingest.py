import os
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, CHUNK_SIZE, CHUNK_OVERLAP, EMBED_MODEL, PDF_DIR
from ocr import extract_text_from_pdf

# 초기화
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer(EMBED_MODEL)


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """텍스트를 청크로 분할"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def is_already_registered(filename):
    """이미 DB에 등록된 파일인지 확인"""
    result = supabase.table("documents").select("id").eq("filename", filename).execute()
    return len(result.data) > 0


def register_pdf(pdf_path):
    """PDF 한 개를 처리해서 DB에 저장"""
    filename = os.path.basename(pdf_path)

    if is_already_registered(filename):
        print(f"스킵 (이미 등록됨): {filename}")
        return

    print(f"처리 중: {filename}")
    text = extract_text_from_pdf(pdf_path)
    chunks = split_text(text)

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        embedding = model.encode(chunk).tolist()
        supabase.table("documents").insert({
            "filename": filename,
            "chunk_index": i,
            "content": chunk,
            "embedding": embedding
        }).execute()

    print(f"완료: {filename} ({len(chunks)}개 청크)")


def run_ingest():
    """PDF 폴더 전체 처리"""
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    print(f"총 {len(pdf_files)}개 PDF 발견")

    for pdf_file in tqdm(pdf_files, desc="등록 중"):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        try:
            register_pdf(pdf_path)
        except Exception as e:
            print(f"오류: {pdf_file} - {e}")


if __name__ == "__main__":
    run_ingest()