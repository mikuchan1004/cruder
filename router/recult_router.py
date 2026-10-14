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

# 이거는 지피티가 짜준 예시 코드라고 생각하면 될거같음..

@router.get('/jobgogo/recult')
def recult(
    request: Request,
    keyword: str = "",
    page: int = 1,
    session: Session = Depends(get_session)
):
    # 한 페이지당 9개
    limit = 9

    # 페이지 번호 계산
    if page<1:
        page=1     
    
    offset = (page - 1) * limit

    search_keyword = f'%{keyword}%'

    # 채용공고 조회
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

    return templates.TemplateResponse(
        request=request,
        name='recult.html',
        context={
            'jobs': jobs,
            'keyword': keyword,
            'page': page,
            'total_pages': total_pages,
            'user_id': request.session.get('user_id'),
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )