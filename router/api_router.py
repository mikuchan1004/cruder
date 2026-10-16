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

# 채용정보 관련 API를 모아두는 라우터
router = APIRouter(tags=['채용정보 관련 라우터'])
session = requests.Session()

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
# 2. Elasticsearch에 채용정보 저장
# ==============================================================================
def save_jobs_to_es(jobs):
    # 엘라스틱서치 저장
    actions = []

    # ALIO에서 받아온 채용공고를 하나씩 처리
    for job in jobs:
        # 채용공고 고유번호
        recrut_pblnt_sn = job.get('recrutPblntSn')

        # 고유번호가 없는 데이터는 Elasticsearch 문서 ID로 사용할 수 없으므로 제외
        if recrut_pblnt_sn is None:
            continue

        # Elasticsearch bulk 저장 형식으로 변환
        actions.append({
            # 저장할 Elasticsearch 인덱스 이름
            '_index': 'alio_jobs',

            # 채용공고 고유번호를 Elasticsearch 문서 ID로 사용
            '_id': str(recrut_pblnt_sn),

            # 실제로 Elasticsearch에 저장할 내용
            '_source': job
        })

    # 저장할 데이터가 하나 이상 있을 때만 실행
    if not actions:
        return 0

    success_count, _ = helpers.bulk(
        es,
        actions
    )

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

def jobs_save_db(jobs,session):
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

        # mariaDB 날짜 포맷 저장할때 하라는건데(gpt 피드백임)
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
    
    

# 이거는 함수 테스트용
@router.post('/jobs/sync')
def insert_data(session: Session = Depends(get_session)): 
    jobs = fetch_jobs()
    jobs_save_db(jobs,session)
    es_count = save_jobs_to_es(jobs)

    print('저장 성공이니!')

    return{'msg':'채용공고 저장 성공!',
           'count':len(jobs),
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
