from sentence_transformers import SentenceTransformer
from supabase import create_client
from groq import Groq
from config import SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY, EMBED_MODEL, TOP_K

# 초기화
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer(EMBED_MODEL)
groq_client = Groq(api_key=GROQ_API_KEY)


def search_similar_chunks(question, top_k=TOP_K):
    """질문과 유사한 청크 검색"""
    question_embedding = model.encode(question).tolist()
    
    result = supabase.rpc("match_documents", {
        "query_embedding": question_embedding,
        "match_count": top_k
    }).execute()
    
    return result.data


def ask(question):
    """질문하고 답변 받기"""
    chunks = search_similar_chunks(question)
    
    if not chunks:
        return "관련 내용을 찾을 수 없습니다.", []

    # 검색된 청크들을 컨텍스트로 합치기
    context = "\n\n".join([
        f"[출처: {c['filename']}]\n{c['content']}" 
        for c in chunks
    ])

    prompt = f"""당신은 사용설명서 전문 도우미입니다.
아래 자료를 바탕으로 질문에 답변해주세요.
자료에 없는 내용은 "해당 내용을 찾을 수 없습니다"라고 답변하세요.

자료:
{context}

질문: {question}

답변:"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    answer = response.choices[0].message.content
    sources = list(set([c['filename'] for c in chunks]))
    
    return answer, sources


if __name__ == "__main__":
    while True:
        question = input("\n질문을 입력하세요 (종료: q): ")
        if question.lower() == "q":
            break
        answer, sources = ask(question)
        print(f"\n답변: {answer}")
        print(f"\n출처: {', '.join(sources)}")