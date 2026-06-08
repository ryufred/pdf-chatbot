# 📄 PDF 문서 챗봇

## 파일 구조
```
📁 프로젝트
├── app.py            ← 사용자용 챗봇 (메인)
├── admin.py          ← 관리자용 PDF 등록
├── requirements.txt
└── 📁 docs/          ← 추출된 텍스트 저장 (자동 생성)
```

## Streamlit Cloud 배포

### 1. GitHub 레포에 파일 올리기
`app.py`, `admin.py`, `requirements.txt` 업로드

### 2. 메인 앱 배포
share.streamlit.io → New app → `app.py` 선택

### 3. 관리자 앱 배포 (별도)
share.streamlit.io → New app → `admin.py` 선택
(같은 레포, 다른 앱으로 배포)

### 4. Secrets 설정
두 앱 모두 Settings → Secrets:
```toml
GEMINI_API_KEY = "AIza..."
ADMIN_PASSWORD = "원하는비밀번호"
```

## 사용 방법
1. 관리자 앱(admin.py)에서 PDF 업로드 → 등록
2. 사용자 앱(app.py)에서 질문 → 출처 포함 답변
3. 새로고침해도 문서 유지 ✅
