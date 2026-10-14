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


# 공지사항 목록 조회
@router.get('/jobgogo/notice')
def commNotice(
    request: Request,
    keyword: str = '',
    page: int = 1,
    session: Session = Depends(get_session)
):
    keyword = keyword.strip()

    if page < 1:
        page = 1

    page_size = 10
    page_start = (page - 1) * page_size

    sql_notice = text('''
        SELECT
            notice_id,
            notice_title,
            notice_detail,
            notice_date,
            user_id
        FROM notice
        WHERE (
            :keyword = ''
            OR notice_title LIKE :search_keyword
            OR notice_detail LIKE :search_keyword
        )
        ORDER BY notice_id DESC
        LIMIT :page_start, :page_size
    ''')

    params = {
        'keyword': keyword,
        'search_keyword': '%' + keyword + '%',
        'page_start': page_start,
        'page_size': page_size
    }

    notice_list = session.execute(
        sql_notice, params
    ).mappings().fetchall()

    sql_count = text('''
        SELECT COUNT(*) AS notice_count
        FROM notice
        WHERE (
            :keyword = ''
            OR notice_title LIKE :search_keyword
            OR notice_detail LIKE :search_keyword
        )
    ''')

    notice_count = session.execute(
        sql_count,
        {
            'keyword': keyword,
            'search_keyword': '%' + keyword + '%'
        }
    ).scalar_one()

    total_page = (notice_count + page_size - 1) // page_size

    return templates.TemplateResponse(
        request=request,
        name='notice.html',
        context={
            'notice_list': notice_list,
            'keyword': keyword,
            'page': page,
            'total_page': total_page,

            'user_id': request.session.get('user_id'),
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )


# 공지사항 상세 조회
@router.get('/notice/{notice_id}')
def notice_detail(
    request: Request,
    notice_id: int,
    session: Session = Depends(get_session)
):
    sql = text('''
        SELECT
            notice_id,
            notice_title,
            notice_detail,
            notice_date,
            user_id
        FROM notice
        WHERE notice_id = :notice_id
    ''')

    notice = session.execute(
        sql,
        {'notice_id': notice_id}
    ).mappings().first()

    if notice is None:
        return popup_error("해당 게시글이 존재하지 않습니다")

    return templates.TemplateResponse(
        request=request,
        name='notice-read.html',
        context={'notice': notice}
    )


# 공지사항 글쓰기 화면
@router.get('/write')
def write_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='write.html',
        context={
            'user_id': request.session.get('user_id'),
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )


# 공지사항 글 등록
@router.post('/notice/write')
def noticeWriteData(
    request: Request,
    notice_title: str = Form(),
    notice_detail: str = Form(),
    session: Session = Depends(get_session)
):
    user_id = request.session.get('user_id')

    adminchk = text('''
        SELECT user_status_id
        FROM user
        WHERE user_id = :user_id
        '''
    )
    adm_chk=session.execute(adminchk, {"user_id" :user_id}).scalar_one_or_none()

    if adm_chk != 1:
        return RedirectResponse(
            url='/error-404',
            status_code=303
        )

    if notice_title.strip() == '' or notice_detail.strip() == '':
        return RedirectResponse(
            url='/write',
            status_code=303
        )

    notice_date = datetime.now()

    sql = text('''
        INSERT INTO notice (
            notice_title,
            notice_detail,
            notice_date,
            user_id
        )
        VALUES (
            :notice_title,
            :notice_detail,
            :notice_date,
            :user_id
        )
    ''')

    session.execute(
        sql,
        {
            'notice_title': notice_title,
            'notice_detail': notice_detail,
            'notice_date': notice_date,
            'user_id': user_id
        }
    )

    session.commit()

    return RedirectResponse(
        url='/notice',
        status_code=303
    )