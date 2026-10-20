
import os
import requests





from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from elasticsearch import Elasticsearch, helpers

from config import ALIO_API_KEY, ELASTIC_ENDPOINT


load_dotenv()

router = APIRouter(tags=["GPT 임베딩 테스트"])

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

es = Elasticsearch(ELASTIC_ENDPOINT)

INDEX_NAME = "alio_jobs_gpt"
MODEL_NAME = "text-embedding-3-small"


# ==========================================
# 1. ALIO 채용공고 가져오기
# ==========================================

def fetch_jobs():

    url = "https://opendata.alio.go.kr/new/v1/recruit/list.do"

    params = {
        "serviceKey": ALIO_API_KEY,
        "resultType": "json",
        "pageNo": 1,
        "numOfRows": 1000
    }

    headers = {
        "accept": "application/json",
        "swaggerType": "Y"
    }

    response = requests.post(
        url,
        params=params,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("result", [])


# ==========================================
# 2. OpenAI 임베딩 함수
# ==========================================

def get_embedding(content):

    response = client.embeddings.create(
        model=MODEL_NAME,
        input=content
    )

    return response.data[0].embedding


# ==========================================
# 3. Elasticsearch 인덱스 생성
# ==========================================

@router.post("/gpt/embed/create")
def create_embed_index():

    if es.indices.exists(index=INDEX_NAME):
        return {"message": "이미 존재합니다!"}

    es.indices.create(
        index=INDEX_NAME,
        mappings={
            # 매핑 작업을 진행합니다.
            "properties": {
                "recrutPblntSn": {"type": "keyword"},
                "recrutPbancTtl": {"type": "text"},
                "instNm": {"type": "text"},
                "workRgnNmLst": {"type": "text"},
                "content": {"type": "text"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1536,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    )

    return {"message": "GPT 임베딩 인덱스 생성 성공!"}


# ==========================================
# 4. ALIO 공고 임베딩 후 ES 저장
# ==========================================

@router.post("/gpt/embed/save")
def save_jobs_to_es(limit: int = 3):

    if not 1 <= limit <= 1000:
        raise HTTPException(
            status_code=400,
            detail="limit은 1~1000 사이여야 합니다."
        )

    if not es.indices.exists(index=INDEX_NAME):
        raise HTTPException(
            status_code=400,
            detail="먼저 /gpt/embed/create를 실행하세요."
        )

    jobs = fetch_jobs()

    actions = []

    for job in jobs[:limit]:

        doc_id = job.get("recrutPblntSn")

        if doc_id is None:
            continue

        doc_id = str(doc_id)

        if es.exists(index=INDEX_NAME, id=doc_id):
            print(f"{doc_id}: 이미 저장된 공고입니다.")
            continue

        title = job.get("recrutPbancTtl") or ""
        inst_name = job.get("instNm") or ""
        region = job.get("workRgnNmLst") or ""
        recrut_name = job.get("recrutSeNm") or ""

        content = f"""
        채용공고: {title}
        기관명: {inst_name}
        근무지역: {region}
        채용구분: {recrut_name}
        """.strip()

        print("임베딩 시작:", title, flush=True)

        embedding = get_embedding(content)

        job_data = job.copy()
        job_data["content"] = content
        job_data["embedding"] = embedding

        actions.append({
            "_index": INDEX_NAME,
            "_id": doc_id,
            "_source": job_data
        })

        print("임베딩 성공:", len(embedding), flush=True)

    success_count = 0

    if actions:
        success_count, _ = helpers.bulk(es, actions)

    return {
        "message": "GPT 임베딩 저장 완료",
        "alio_count": len(jobs),
        "saved_count": success_count
    }



# ==========================================
# 5. GPT 하이브리드 검색 (BM25 + KNN + RRF)
# ==========================================

def hybrid_gpt(keyword):

    print("GPT 하이브리드 검색 시작")

    # 검색어 임베딩
    vector_keyword = get_embedding(keyword)

    # 실제 저장된 문서 수 확인
    doc_count = es.count(index=INDEX_NAME)["count"]

    if doc_count == 0:
        return {"hits": {"hits": []}}

    search_size = min(50, doc_count)

    # BM25 키워드 검색
    text_response = es.search(
        index=INDEX_NAME,
        query={
            "multi_match": {
                "query": keyword,
                "fields": [
                    "recrutPbancTtl",
                    "instNm",
                    "workRgnNmLst",
                    "content"
                ]
            }
        },
        size=search_size,
        source_excludes=["embedding"]
    )

    # GPT 벡터 검색
    vector_response = es.search(
        index=INDEX_NAME,
        knn={
            "field": "embedding",
            "query_vector": vector_keyword,
            "k": search_size,
            "num_candidates": max(100, search_size)
        },
        size=search_size,
        source_excludes=["embedding"]
    )

    # RRF 점수 계산
    rrf_score = {}
    rank_constant = 60

    for response in [text_response, vector_response]:

        for rank, hit in enumerate(
            response["hits"]["hits"], start=1
        ):

            doc_id = hit["_id"]

            if doc_id not in rrf_score:
                rrf_score[doc_id] = {
                    "score": 0,
                    "source": hit["_source"]
                }

            rrf_score[doc_id]["score"] += (
                1 / (rank_constant + rank)
            )

    results = sorted(
        rrf_score.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    hits = []

    for doc_id, data in results[:10]:

        hits.append({
            "_id": doc_id,
            "_score": data["score"],
            "_source": data["source"]
        })

    return {
        "hits": {
            "hits": hits,
            "total": {"value": len(rrf_score)}
        }
    }


# ==========================================
# 6. GPT 하이브리드 검색 Swagger 테스트
# ==========================================

@router.get(
    "/gpt/embed/search",
    summary="GPT 하이브리드 채용공고 검색"
)
def search_jobs(keyword: str):

    return hybrid_gpt(keyword)


# ==========================================
# 7. chatjoppt GPT RAG 답변 생성
# ==========================================

@router.get(
    "/gpt/embed/ask",
    summary="chatjoppt GPT 맞춤 채용 추천",
    description="ALIO 채용공고를 하이브리드 검색한 뒤 GPT가 추천 답변을 생성합니다."
)
def ask_gpt(question: str):

    # 하이브리드 검색
    results = hybrid_gpt(question)["hits"]["hits"]

    if not results:
        return {
            "question": question,
            "answer": "현재 저장된 채용공고 중 조건에 부합하는 공고를 찾지 못했습니다.",
            "count": 0,
            "jobs": []
        }

    # 검색 결과를 GPT용 context로 가공
    contexts = []

    for idx, result in enumerate(results, start=1):

        job = result["_source"]

        contexts.append(f"""
        [검색 결과: {idx}]
        공고번호: {job.get('recrutPblntSn', '')}
        제목: {job.get('recrutPbancTtl', '')}
        기관명: {job.get('instNm', '')}
        근무지역: {job.get('workRgnNmLst', '')}
        채용구분: {job.get('recrutSeNm', '')}
        채용인원: {job.get('recrutNope', '')}
        직무분야: {job.get('ncsCdNmLst', '')}
        고용형태: {job.get('hireTypeNmLst', '')}
        지원자격: {job.get('aplyQlfcCn', '')}
        학력조건: {job.get('acbgCondNmLst', '')}
        공고시작일: {job.get('pbancBgngYmd', '')}
        공고종료일: {job.get('pbancEndYmd', '')}
        채용진행여부: {job.get('ongoingYn', '')}
        원문링크: {job.get('srcUrl', '')}
        """)

    context = "\n--------\n".join(contexts)

    # chatjoppt 시스템 프롬프트
    system_prompt = """
    너는 공공기관 채용정보 전문 AI 도우미
    'chatjoppt'야.

    사용자의 질문을 분석하고,
    제공된 ALIO 채용공고를 바탕으로
    적합한 공공기관 채용정보를 추천해.

    [기본 규칙]
    1. 반드시 검색된 context를 근거로 답변해.
    2. 존재하지 않는 채용공고를 만들어내지 마.
    3. 기관명, 채용조건, 근무지역, 급여 등을 지어내지 마.
    4. 자연스러운 한국어 존댓말로 답변해.
    5. 불필요한 설명이나 반복은 생략해.
    6. 채용공고의 사실과 AI의 판단을 구분해.

    [사용자 조건 분석]
    다음 조건을 질문에서 파악해.

    - 희망 근무지역
    - 관심 직무
    - 신입 또는 경력 여부
    - 전공 및 학력
    - 보유 자격증
    - 프로그래밍 기술 및 업무 경험
    - 기타 희망 조건

    언급하지 않은 조건은 임의로 설정하지 마.

    [추천 규칙]
    1. 사용자 조건과 관련성이 높은 순서로 추천해.
    2. 최대 5개의 채용공고를 추천해.
    3. 같은 공고는 중복 추천하지 마.
    4. 조건이 일부 일치하면 차이점을 설명해.
    5. 확인되지 않은 지원 자격은 단정하지 마.
    6. 공고 마감 여부는 제공된 날짜와 상태를 확인해.
    7. 정보가 부족하면 '정보 없음'으로 표시해.
    8. 원문 URL은 context의 주소만 사용해.

    [답변 형식]

    사용자님의 조건과 관련된
    공공기관 채용공고를 안내해 드리겠습니다.

    1. 기관명:
       채용공고:
       근무지역:
       채용구분:
       접수기간:
       추천 이유:
       공고 링크:

    검색된 실제 공고 수에 맞게 작성해.

    [검색 결과가 부족한 경우]
    적합한 공고가 없으면 다음과 같이 답변해.

    '현재 검색된 채용공고 중 조건에
    부합하는 공고를 찾지 못했습니다.'

    검색 결과가 없다고 해서
    실제 채용공고가 존재하지 않는다고 단정하지 마.

    채용 추천이 아닌 일반 질문에는
    자연스러운 답변을 제공해.
    """

    user_prompt = f"""
    [사용자 질문]
    {question}

    [검색된 ALIO 채용공고]
    {context}

    위 자료를 바탕으로 사용자에게 답변해.
    """

    # GPT 답변 생성
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3
    )

    answer = response.choices[0].message.content

    print("GPT RAG 답변 생성 성공")

    return {
        "question": question,
        "answer": answer,
        "count": len(results),
    "jobs": [
    {
        "recrutPblntSn": hit["_source"].get("recrutPblntSn"),
        "recrutPbancTtl": hit["_source"].get("recrutPbancTtl"),
        "instNm": hit["_source"].get("instNm"),
        "workRgnNmLst": hit["_source"].get("workRgnNmLst"),
        "recrutSeNm": hit["_source"].get("recrutSeNm"),
        "recrutNope": hit["_source"].get("recrutNope"),
        "pbancBgngYmd": hit["_source"].get("pbancBgngYmd"),
        "pbancEndYmd": hit["_source"].get("pbancEndYmd"),
        "ongoingYn": hit["_source"].get("ongoingYn"),
        "srcUrl": hit["_source"].get("srcUrl")
    }
            for hit in results
        ]
    }
