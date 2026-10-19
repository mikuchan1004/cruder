from elasticsearch import Elasticsearch, helpers
import requests
from fastapi import APIRouter
from sqlalchemy import text
from database import engine
from datetime import datetime,date
from config import ALIO_API_KEY, ELASTIC_ENDPOINT
from sqlalchemy import text
from database import get_session
from fastapi import FastAPI, Depends
from sqlmodel import Session
from config import GEMINI_API_KEY
from google import genai

from util import formatter
# 채용정보 관련 API를 모아두는 라우터
router = APIRouter(tags=['채용정보 관련 라우터'])
session = requests.Session()


''''
다소 부끄럽지만 이쪽은 GPT 피드백이 다수입니다
그래도 기존의 임베딩 로직은 비슷하다는 점
양해 부탁드립니다.



'''




# Elasticsearch 연결
# 현재는 기존 run.py에서 사용하던 로컬 Elasticsearch 주소를 그대로 유지
es = Elasticsearch(
    ELASTIC_ENDPOINT
)
 

# ==============================================================================
# 1. ALIO 채용정보 가져오기(이거를 활용해서 MariaDB에 실제로 넣어야함)
# ==============================================================================
def fetch_jobs():
    # 청년 일자리 채용정보 목록 Open API 주소
    url = 'https://opendata.alio.go.kr/new/v1/recruit/list.do'

    # ALIO API에 전달할 Query Parameter
    params = {
        # 발급받은 인증키
        'serviceKey': ALIO_API_KEY,
        # 응답 형식을 JSON으로 요청
        'resultType': 'json',
        # 조회할 페이지 번호
        'pageNo': 1,
        # 한 번에 가져올 데이터 개수
        'numOfRows': 1000
    }

    # HTTP 요청에 같이 전달할 Header
    headers = {
        # JSON 형태의 응답을 원한다고 서버에 알림
        'accept': 'application/json',
        # ALIO Swagger에서 사용하는 헤더
        'swaggerType': 'Y'
    }

    # ALIO Open API에 POST 방식으로 채용정보 요청
    response = requests.post(
        url,
        params=params,
        headers=headers
    )

    # HTTP 요청 자체가 실패한 경우 예외 발생
    response.raise_for_status()

    # ALIO가 반환한 JSON 데이터를
    # Python 딕셔너리로 변환
    data = response.json()

    # result가 없을 경우 빈 리스트 반환
    return data.get('result', [])
 

# ==============================================================================
# 2. Elasticsearch에 채용정보 저장(가장 중요한 부분임!)
# ==============================================================================

import time

def save_jobs_to_es(jobs):
    actions = []
    success_count = 0

    print("ES 서버 연결 확인 시작", flush=True)
    print("ES 연결 결과:", es.ping(), flush=True)

    for job in jobs:
        recrut_pblnt_sn = job.get('recrutPblntSn')

        if recrut_pblnt_sn is None:
            continue

        doc_id = str(recrut_pblnt_sn)

        print(f"{doc_id}: ES 중복 확인 시작", flush=True)

        if es.exists(index='alio_jobs', id=doc_id):
            existing = es.get(
                index='alio_jobs',
                id=doc_id,
                source_includes=['embedding', 'content']
            )['_source']

            if existing.get('embedding'):
                print(f'{doc_id}: 이미 임베딩된 공고입니다.')
                continue

        print(f"{doc_id}: 임베딩 생성 시작", flush=True)

        # 이하 기존 코드 그대로 유지
        title = job.get('recrutPbancTtl') or ''
        inst_name = job.get('instNm') or ''
        region = job.get('workRgnNmLst') or ''
        recrut_name = job.get('recrutSeNm') or ''

        content = f'''
        채용공고: {title}
        기관명: {inst_name}
        근무지역: {region}
        채용구분: {recrut_name}
        '''.strip()

        # Gemini 임베딩 생성
        while True:
            try:
                embedding = get_embedding_with_llm(title, content)
                break

            except Exception as e:
                error_message = str(e)

                if '429' in error_message:
                    print('Gemini 요청 제한! 20초 후 재시도')
                    time.sleep(20)
                else:
                    raise

        job_data = job.copy()
        job_data['content'] = content
        job_data['embedding'] = embedding

        actions.append({
            '_index': 'alio_jobs',
            '_id': doc_id,
            '_source': job_data
        })

        # 50개씩 나누어 저장
        if len(actions) >= 50:
            count, _ = helpers.bulk(es, actions)
            success_count += count

            print(f'현재 저장된 공고: {success_count}개')
            actions = []

    # 마지막에 남은 데이터 저장
    if actions:
        count, _ = helpers.bulk(es, actions)
        success_count += count

    return success_count


# ==============================================================================
# 3. 검색어로 채용정보 필터링
# ==============================================================================
def filter_jobs(jobs, keyword):
    # 검색하기 편하도록 앞뒤 공백 제거 + 소문자 변환
    keyword = keyword.strip().lower()

    filtered_jobs = []

    # 가져온 채용공고를 하나씩 검사
    for job in jobs:

        # 채용공고 제목
        title = job.get('recrutPbancTtl', '')

        # 기관명
        inst_name = job.get('instNm', '')

        # NCS 직무분야 이름
        ncs_name = job.get('ncsCdNmLst', '')

        # 제목에서 기관명 제거
        search_title = title.replace(inst_name, '')

        # 채용공고 제목 또는 NCS 직무분야 이름에
        # 사용자가 입력한 검색어가 포함되어 있는지 검사
        if (
            keyword in search_title.lower()
            or keyword in ncs_name.lower()
        ):
            filtered_jobs.append(job)

    return keyword, filtered_jobs

 


# 채용공고 저장하는 곳.
def jobs_save_db(jobs,session):
    print('잘 저장되니?')
    for job in jobs:
        
        recrutPblntSn= job.get('recrutPblntSn')
        recrutPbancTtl=job.get('recrutPbancTtl')
        instNm=job.get('instNm')
        pbancBgngYmd=job.get('pbancBgngYmd')
        pbancEndYmd=job.get('pbancEndYmd')
        srcUrl=job.get('srcUrl')
        ongoingYn=job.get('ongoingYn')
        recrutSeNm=job.get('recrutSeNm')
        recrutNope=job.get('recrutNope')
        workRgnNmLst=job.get('workRgnNmLst')
        
        # 만약에 공고 번호가 없으면 저장  x
        if recrutPblntSn is None:
            continue
        
        # db에 밀어넣기
        sql = text('''
            insert into jobs(
                recrut_pblnt_sn,
                recrut_pbanc_ttl,
                inst_nm,
                pbanc_bgng_ymd,
                pbanc_end_ymd,
                src_url,
                ongoing_yn,
                recrut_se_nm,
                recrut_nope,
                work_rgn_nm_lst     
            )
            values(
                :recrut_pblnt_sn,
                :recrut_pbanc_ttl,
                :inst_nm,
                :pbanc_bgng_ymd,
                :pbanc_end_ymd,
                :src_url,
                :ongoing_yn,
                :recrut_se_nm,
                :recrut_nope,
                :work_rgn_nm_lst          
            )
            on duplicate key update
            recrut_pblnt_sn=:recrut_pblnt_sn,
            recrut_pbanc_ttl=:recrut_pbanc_ttl,
            inst_nm=:inst_nm,
            pbanc_bgng_ymd=:pbanc_bgng_ymd,
            pbanc_end_ymd=:pbanc_end_ymd,
            src_url=:src_url,
            ongoing_yn=:ongoing_yn,
            recrut_se_nm=:recrut_se_nm,
            recrut_nope=:recrut_nope,
            work_rgn_nm_lst=:work_rgn_nm_lst
        ''')

        # maria db

        '''
        mariaDB 날짜 포맷 저장할때 하라는건데(gpt 피드백임)입니다
        ''' 
        if pbancBgngYmd:
                pbancBgngYmd = str(pbancBgngYmd)
                pbancBgngYmd = (
                pbancBgngYmd[:4] + '-' +
                pbancBgngYmd[4:6] + '-' +
                pbancBgngYmd[6:8]
            )

        if pbancEndYmd:
            pbancEndYmd = str(pbancEndYmd)
            pbancEndYmd = (
                pbancEndYmd[:4] + '-' +
                pbancEndYmd[4:6] + '-' +
                pbancEndYmd[6:8]
            )

        # sql문을 실행
        session.exec(sql, params={
            'recrut_pblnt_sn': recrutPblntSn,
            'recrut_pbanc_ttl': recrutPbancTtl,
            'inst_nm': instNm,
            'pbanc_bgng_ymd': pbancBgngYmd,
            'pbanc_end_ymd': pbancEndYmd,
            'src_url': srcUrl,
            'ongoing_yn': ongoingYn,
            'recrut_se_nm': recrutSeNm,
            'recrut_nope': recrutNope,
            'work_rgn_nm_lst': workRgnNmLst
        })
         
    session.commit()
    
    

# DB에 채용 공고를 저장한다.
@router.post('/jobs/sync')
def insert_data(session: Session = Depends(get_session)):

    print("1. ALIO 호출 시작")

    jobs = fetch_jobs()
    print("2. ALIO 호출 성공", len(jobs))

    jobs_save_db(jobs, session)
    print("3. MariaDB 저장 성공")
    #  저장 테스트 소량으로 진행
    es_count = save_jobs_to_es(jobs[:3])
    print("4. Elasticsearch 저장 성공")

    return {
        'msg': '채용공고 저장 성공!',
        'count': len(jobs),
        'elasticsearch_count': es_count
    }

# 필터링 테스트입니다. 
@router.post('/jobs/filter_jobs')
def filter_date(keyword:str="", session: Session = Depends(get_session)):
    all_jobs=fetch_jobs()
   
    _, filtered_jobs = filter_jobs(all_jobs, keyword)
    jobs_save_db(filtered_jobs, session)
    return{
        'msg':f'{keyword}필터링 저장성공이니이!!!!',
          'count': len(filtered_jobs)
    }
    
    
#엠베딩 작업수행

@router.post('/alio/embed/create')
def create_embed_index():

    if es.indices.exists(index='alio_jobs'):
        return '이미 존재합니다!'
          
    es.indices.create(
        index='alio_jobs',
        mappings={
          'properties':{
            # 채용공고번호
            'recrutPblntSn':{'type': 'keyword'},
            #채용 공고 제목
            'recrutPbancTtl':{'type':'text'},
            # 기관명
            'instNm':{'type':'text'},
            # 근무지역
            'workRgnNmLst': {'type': 'text'},

            #  공고시작일
           'pbancBgngYmd': {'type': 'date', 'format': 'yyyyMMdd||yyyy-MM-dd'},
             #    공고 종료일
             'pbancEndYmd': {'type': 'date', 'format': 'yyyyMMdd||yyyy-MM-dd'},
            #  제미나이한테 할 질문
            "content": {"type": "text"},
            
              "embedding": {
                    "type": "dense_vector",
                    # "dims": 768 # 64의 배수라서 cpu 연산 단위와 호환이 잘 된다
                    #             # 512도 많이 쓴다. 256은 뉘양스에 조금 약하다
                    "dims": 768
                }
          } 
        }
    )   
    # print('인덱스 생성된거 확인용')
    return '인덱스 생성 성공!'

          
      
    

    
    
##################### 제미나이 사용 할곳
######################## 
gemini=genai.Client(api_key=GEMINI_API_KEY)

# gemini에서 사용할 타입들
from google.genai import types
# gemini를 이용해서 백터화 한다
def get_embedding_with_llm(title, content) :
    prompt = f'''
        task: retrival document\n
        title: {title}\n
        content: {content}
            '''
    result = gemini.models.embed_content(
        model='gemini-embedding-2',

        # 텍스트를 임베딩한다
        contents=[
            types.Content(
                parts=[
                    types.Part.from_text(text=prompt)
                ]
            )
        ],

        # 옵션
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )

    return result.embeddings[0].values


# 임베딩 변환



''''
검색어를 벡터로 변환하는 함수입니다.
'''
def get_keyword_embedding_with_llm(keyword) :
    prompt = f'''
        task: retrival query\n
        query: {keyword}
'''
    result = gemini.models.embed_content(
        model='gemini-embedding-2',

        # 텍스트를 임베딩한다
        contents=[
            types.Content(
                parts=[
                    types.Part.from_text(text=prompt)
                ]
            )
        ],

        # 옵션
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )

    return result.embeddings[0].values





'''
수업떄 직접 구현 해 놓은 rrf입니다.

'''


@router.get('/embed/search/hybrid')
def hybrid(keyword) :
    # 라이센스가 없어서(trial에 있는데 클라우드 14일 도커 30일 제한)
    # rrf 직접 구현
    vector_keyword = get_keyword_embedding_with_llm(keyword)
    print('2. 질문 임베딩 성공', len(vector_keyword))

    # BM25 검색
    text_response = es.search(
       
        index="alio_jobs",
        query={
            "multi_match": {
                "query": keyword,
                "fields": ["recrutPbancTtl", 
                           "instNm",
                           "workRgnNmLst",
                           "content"
                           
                           ]
            }
        },
        size=50
    )
    print('3 BM25 성공')

    # 벡터 검색
    vector_response = es.search(
        index="alio_jobs",
        knn={
            "field": "embedding",
            "query_vector": vector_keyword,
            "k": 50,
            "num_candidates": 100
        },
        size=50
    )



    rrf_score = {}
    rank_constant = 60

    for rank, hit in enumerate(text_response["hits"]["hits"], start=1):
        # id를 추출하고
        doc_id = hit['_id']
        if doc_id not in rrf_score:
            rrf_score[doc_id] = {
                "score": 0,
                "source": hit["_source"]
            }
        rrf_score[doc_id]['score'] += (1 / (rank_constant + rank))
    # vector 검색 결과 하나마다
    for rank, hit in enumerate(vector_response["hits"]["hits"], start=1):
        doc_id = hit['_id']
        if doc_id not in rrf_score:
            rrf_score[doc_id] = {
                "score": 0,
                "source": hit["_source"]
            }
        rrf_score[doc_id]['score'] += (1 / (rank_constant + rank))

    print('rrf_score:', rrf_score)
    results = sorted(
        rrf_score.items(), # (key, value) 튜플로
        key=lambda x: x[1]['score'], # items의 두번째 값 즉 value
        reverse=True #내림차순으로 정렬
    )

    # 돌려주고 싶은 개수(즉 조회 결과 수)
    size = 10
    # 기존 formatter가 사용할 수 있도록 Elasticsearch 응답 형태로 변환
    hits = []
    for doc_id, data in results[:size]:
        hits.append({
            "_id": doc_id,
            "_score": data["score"],
            "_source": data["source"]
        })

    resp = {
        "hits": {
            "hits": hits,
            "total": {
                "value": len(rrf_score)
            }
        }
    }
    return resp

# 제미나이를 쓸껀데 우리가 쓸 프롬프트 제작


@router.get('/embed/ask')
def ask_rag(question:str=' '):
    # 하이브리드 검색
    results = hybrid(question)['hits']['hits']

    # 검색 결과를 Gemini용으로 가공
    contexts = []

    for idx, result in enumerate(results):
        job = result['_source']

        contexts.append(f'''
        [검색 결과:{idx}]
        공고번호: {job.get('recrutPblntSn', '')}
        제목: {job.get('recrutPbancTtl', '')}
        기관명: {job.get('instNm', '')}
        근무지역: {job.get('workRgnNmLst', '')}
        채용구분: {job.get('recrutSeNm', '')}
        채용인원: {job.get('recrutNope', '')}
        공고시작일: {job.get('pbancBgngYmd', '')}
        공고종료일: {job.get('pbancEndYmd', '')}
        원문링크: {job.get('srcUrl', '')}
        ''')

    context = "\n--------\n".join(contexts)

    prompt = f'''
    너는 공공기관 채용정보 검색 도우미 chatjoppt야.

    아래의 context에 포함된 내용으로 질문에 답변해줘.

    규칙
    1. 절대 추론이나 다른 내용을 담으면 안 돼.
    2. 내용에 없는 질문이라면 "문서에서 확인할 수 없는 질문입니다"라고 답변해줘.
    3. 한국어로 답변해줘.
    4. 불필요하게 긴 설명을 하지 말아줘.
    5. 답변에 대한 근거를 자연스럽게 설명해줘.
    6. 채용공고를 추천할 때는 기관명과 공고 제목을 알려줘.

    질문: {question}

    context: {context}
    '''.strip()

    print('prompt:', prompt)

    def ask_gemini(prompt):
        response = gemini.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt
        )
        print('ask_gemini', response)
        return response.text

    answer = ask_gemini(prompt)
    print('answer:', answer)

    return answer