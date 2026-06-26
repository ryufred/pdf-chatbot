import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
from tqdm import tqdm

def extract_text_from_pdf(pdf_path):
    """PDF에서 텍스트 추출 (일반 텍스트 + OCR 혼합)"""
    doc = fitz.open(pdf_path)
    full_text = ""

    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. 일반 텍스트 먼저 시도
        text = page.get_text("blocks")  # "blocks"로 바꾸면 블록 단위로 순서대로 읽음

        # blocks는 튜플 리스트로 나오니까 텍스트만 추출
        if isinstance(text, list):
            text = "\n".join([b[4] for b in sorted(text, key=lambda b: (b[1], b[0])) if isinstance(b[4], str)])
        
        # 2. 텍스트가 거의 없으면 OCR로 처리 (이미지 PDF)
        if len(text.strip()) < 50:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(img, lang="kor+eng", config="--psm 6 --oem 3")
        
        full_text += f"\n[페이지 {page_num + 1}]\n{text}"
    
    doc.close()
    return full_text


def process_all_pdfs(pdf_dir, output_dir="./texts"):
    """폴더 안의 모든 PDF 처리"""
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    print(f"총 {len(pdf_files)}개 PDF 발견")

    for pdf_file in tqdm(pdf_files, desc="PDF 처리 중"):
        pdf_path = os.path.join(pdf_dir, pdf_file)
        output_path = os.path.join(output_dir, pdf_file.replace(".pdf", ".txt"))
        
        # 이미 처리된 파일 스킵
        if os.path.exists(output_path):
            continue
        
        try:
            text = extract_text_from_pdf(pdf_path)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            print(f"오류: {pdf_file} - {e}")

    print("완료!")


if __name__ == "__main__":
    from config import PDF_DIR
    process_all_pdfs(PDF_DIR)