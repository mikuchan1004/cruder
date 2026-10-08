from elasticsearch import Elasticsearch, helpers
import requests
from fastapi import APIRouter

from config import ALIO_API_KEY, ELASTIC_ENDPOINT


# 채용정보 관련 API를 모아두는 라우터
router = APIRouter(tags=['채용정보 관련 라우터'])

# Elasticsearch 연결
# 현재는 기존 run.py에서 사용하던 로컬 Elasticsearch 주소를 그대로 유지
es = Elasticsearch(
    ELASTIC_ENDPOINT
)
 

# ==============================================================================
# 1. ALIO 채용정보 가져오기
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
        'numOfRows': 500
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
# 2. Elasticsearch에 채용정보 저장
# ==============================================================================
# def save_jobs_to_es(jobs):
#     # 엘라스틱서치 저장
#     actions = []

#     # ALIO에서 받아온 채용공고를 하나씩 처리
#     for job in jobs:
#         # 채용공고 고유번호
#         recrut_pblnt_sn = job.get('recrutPblntSn')

#         # 고유번호가 없는 데이터는 Elasticsearch 문서 ID로 사용할 수 없으므로 제외
#         if recrut_pblnt_sn is None:
#             continue

#         # Elasticsearch bulk 저장 형식으로 변환
#         actions.append({
#             # 저장할 Elasticsearch 인덱스 이름
#             '_index': 'alio_jobs',

#             # 채용공고 고유번호를 Elasticsearch 문서 ID로 사용
#             '_id': recrut_pblnt_sn,

#             # 실제로 Elasticsearch에 저장할 내용
#             '_source': job
#         })

#     # 저장할 데이터가 하나 이상 있을 때만 실행
#     if actions:
#         # actions에 담긴 모든 채용공고를
#         # Elasticsearch에 한 번에 저장
#         helpers.bulk(es, actions)


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

 
# ==============================================================================
# 4. 채용정보 조회 API
# ==============================================================================
# GET /jobs?keyword=검색어
# 형태로 요청할 수 있는 API
@router.get('/jobs')
def get_jobs(keyword: str):
    # ALIO Open API에서 채용정보 가져오기
    jobs = fetch_jobs()

    # 가져온 채용정보를 Elasticsearch에 저장
    # save_jobs_to_es(jobs)

    # 검색어를 기준으로 채용정보 필터링
    keyword, filtered_jobs = filter_jobs(jobs, keyword)

    # Swagger / 프론트에 반환할 최종 응답
    return {
        'keyword': keyword,
        'count': len(filtered_jobs),
        'result': filtered_jobs
    }


# ==============================================================================
# 과거 ALIO API 요청 방식 테스트 코드
# 공부용으로 남겨둠
# ==============================================================================

# print('ALIO_API_KEY 존재:', ALIO_API_KEY is not None)
# print('ALIO_API_KEY 길이:', len(ALIO_API_KEY) if ALIO_API_KEY else 0)


# response = requests.get(
#     url,
#     params=params,
#     allow_redirects=False
# )

# return {
#     'status_code': response.status_code,
#     'response': response.text
# }

# response = requests.get(
#     'https://opendata.alio.go.kr/new/v1/recruit/list.do',
#     params=params,
#     allow_redirects=False
# )

# return {
#     'status_code': response.status_code,
#     'location': response.headers.get('Location'),
#     'content_type': response.headers.get('Content-Type'),
#     'response': response.text