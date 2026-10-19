from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, create_engine,text

from database import get_session


router = APIRouter()
templates = Jinja2Templates(directory='templates/')


# =========================================================
# assets 폴더 연결
# =========================================================

router.mount(
    "/assets",
    StaticFiles(directory="assets"),
    name="assets"
)

# =========================================================
# static 폴더 연결
# =========================================================

router.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


##########################################################
# 메인 페이지 접속 라우팅
########################################################## 



@router.get('/jobgogo/recult')
def recult(
    request: Request,
    keyword: str = "",
    page: int = 1,
    session: Session = Depends(get_session)
):
    print('취업 공고 사이트 접속 성공!')
    # 혹시 모를 공백을 제거한다.
    
    keyword=keyword.strip()
    # 한 페이지당 9개
    search_keyword = f'%{keyword}%'
    # 페이지 번호 계산
    if page<1:
        page=1 
    
    # 한 페이지에 게시물 9개싞 보여줌
    limit = 9
    offset = (page - 1) * limit

    # 데이터 베이스에서 채용 중인 항목만 조회함
    sql = text('''
        SELECT *
        FROM jobs
        WHERE ongoing_yn = 'Y'
        AND (
            recrut_pbanc_ttl LIKE :keyword
            OR inst_nm LIKE :keyword
            OR work_rgn_nm_lst LIKE :keyword
        )
        ORDER BY pbanc_bgng_ymd DESC, recrut_pblnt_sn DESC
        LIMIT :limit OFFSET :offset
    ''')

    result = session.exec(
        sql,
        params={
            'keyword': search_keyword,
            'limit': limit,
            'offset': offset
        }
    )

    jobs = result.mappings().fetchall()

    # 로그인한 사용자의 찜한 공고 ID 조회
    user_id = request.session.get('user_id')
    bookmarked_job_ids = set()

    if user_id:
        bookmark_sql = text('''
            SELECT recrut_pblnt_sn
            FROM bookmark
            WHERE user_id = :user_id
        ''')

        bookmark_result = session.exec(
            bookmark_sql,
            params={'user_id': user_id}
        )

        bookmarked_job_ids = {
            row[0] for row in bookmark_result.fetchall()
        }

    # 전체 검색 결과 개수 조회
    count_sql = text('''
        SELECT COUNT(*)
        FROM jobs
        WHERE ongoing_yn = 'Y'
        AND (
            recrut_pbanc_ttl LIKE :keyword
            OR inst_nm LIKE :keyword
            OR work_rgn_nm_lst LIKE :keyword
        )
    ''')

    result = session.exec(
        count_sql,
        params={'keyword': search_keyword}
    )
    total_count=result.fetchone()[0]
    

    # 총 페이지 수 계산
    total_pages = (total_count + limit - 1) // limit
    
       # 몇 그룹씩 끊을지 생각하기
    page_group=5
    
    # 시작 페이지 그룹 계산하기
    start_page=((page-1)//5)*page_group+1
    # 마지막 페이지 그룹 계산 
    end_page=start_page+page_group-1
    
    if end_page>total_pages:
        end_page=total_pages
   
    

    return templates.TemplateResponse(
        request=request,
        name='recult.html',
        context={
            'jobs': jobs,
            'keyword': keyword,
            'page': page,
            'total_pages': total_pages,
            'start_page':start_page,
            'end_page':end_page,
            'bookmarked_job_ids': bookmarked_job_ids,
            'user_id': request.session.get('user_id'),
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )

@router.get('/es/health')
def health() :
    connected = es.ping()
    print('엘라스틱서치 연결 상태 : ' , connected)
    return {
        'connected' : connected,
        'msg' : "Elasticsearch 연결 " + "성공"  if connected else "실패"
    }

from elasticsearch import Elasticsearch

es = Elasticsearch(
    'http://192.168.0.46:9200' # DB 연결 주소
)