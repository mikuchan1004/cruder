from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from sqlalchemy import text
from datetime import datetime

from database import get_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def popup_error(message: str):
    import json

    message = json.dumps(message, ensure_ascii=False)
    message = message.replace("<", "\\u003c").replace(">", "\\u003e")

    return HTMLResponse(
        content=f"""
        <script>
            alert({message});
            history.back();
        </script>
        """
    )



@router.get('/jobgogo/mypage/reposts')
def jobtip(
    request: Request,
    keyword: str = '',
    page: int = 1,
    session: Session = Depends(get_session)
):
    print('마이페이지 내가 쓴글 모음')

    # 로그인한 사용자 ID
    user_id = request.session.get('user_id')

    # 로그인하지 않았으면 로그인 페이지로 이동
    if not user_id:
        return RedirectResponse(url='/jobgogo/login', status_code=303)

    keyword = keyword.strip()

    if page < 1:
        page = 1

    page_size = 10
    page_start = (page - 1) * page_size

    # 로그인한 사용자가 작성한 게시글만 조회
    sql_jobtip = text('''
        SELECT
            job_tip_no,
            job_tip_title,
            job_tip_date,
            job_tip_detail,
            user_id
        FROM job_tip
        WHERE user_id = :user_id
        AND (
            :keyword = ''
            OR job_tip_title LIKE :search_keyword
            OR job_tip_detail LIKE :search_keyword
        )
        ORDER BY job_tip_no DESC
        LIMIT :page_start, :page_size
    ''')

    result = session.execute(
        sql_jobtip,
        {
            'user_id': user_id,
            'keyword': keyword,
            'search_keyword': '%' + keyword + '%',
            'page_start': page_start,
            'page_size': page_size
        }
    )

    job_tip_list = result.mappings().fetchall()

    # 로그인한 사용자의 전체 게시글 수
    sql_count = text('''
        SELECT COUNT(*) AS job_tip_count
        FROM job_tip
        WHERE user_id = :user_id
        AND (
            :keyword = ''
            OR job_tip_title LIKE :search_keyword
            OR job_tip_detail LIKE :search_keyword
        )
    ''')

    job_tip_count = session.execute(
        sql_count,
        {
            'user_id': user_id,
            'keyword': keyword,
            'search_keyword': '%' + keyword + '%'
        }
    ).scalar_one()

    total_page = (job_tip_count + page_size - 1) // page_size

    return templates.TemplateResponse(
        request=request,
        name='recent-posts.html',
        context={
            'job_tip_list': job_tip_list,
            'keyword': keyword,
            'page': page,
            'total_page': total_page,
            'user_id': user_id,
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )