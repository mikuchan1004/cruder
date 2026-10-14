import json
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from fastapi import (
    APIRouter, Request, Depends,
    Form, File, UploadFile, HTTPException
)
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from sqlalchemy import text

from database import get_session

router = APIRouter()
templates = Jinja2Templates(directory="templates/")


# 이미지 저장 폴더
UPLOAD_DIR = Path("assets/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp"
}

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


# ==========================================
# 꿀팁 게시판 목록
# ==========================================
@router.get('/jobgogo/jobtip')
def jobtip(
    request: Request,
    keyword: str = '',
    page: int = 1,
    session: Session = Depends(get_session)
):
    print('취업 꿀팁 페이지 접속 성공!')

    keyword = keyword.strip()

    if page < 1:
        page = 1

    # 한 페이지당 게시글 10개
    page_size = 10
    page_start = (page - 1) * page_size

    

    # DB에서 게시글 목록 조회
    sql_jobtip = text('''
        SELECT
            job_tip_no,
            job_tip_title,
            job_tip_date,
            job_tip_detail,
            user_id
        FROM job_tip
        WHERE (
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
            'keyword': keyword,
            'search_keyword': '%' + keyword + '%',
            'page_start': page_start,
            'page_size': page_size
        }
    )

    job_tip_list = result.mappings().fetchall()

    # 검색 조건에 맞는 전체 게시글 수
    sql_count = text('''
        SELECT COUNT(*) AS job_tip_count
        FROM job_tip
        WHERE (
            :keyword = ''
            OR job_tip_title LIKE :search_keyword
            OR job_tip_detail LIKE :search_keyword
        )
    ''')

    job_tip_count = session.execute(
        sql_count,
        {
            'keyword': keyword,
            'search_keyword': '%' + keyword + '%'
        }
    ).scalar_one()

    # 전체 페이지 수
    total_page = (job_tip_count + page_size - 1) // page_size

    # HTML 출력
    return templates.TemplateResponse(
        request=request,
        name='job-tip.html',
        context={
            'job_tip_list': job_tip_list,
            'keyword': keyword,
            'page': page,
            'total_page': total_page,

            # 로그인 세션 유지
            'user_id': request.session.get('user_id'),
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )


# ==========================================
# 꿀팁 게시판 글쓰기 화면
# ==========================================
@router.get('/jobtip/write')
def jobtip_write_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='job-tip-write.html',

    # 로그인 세션
    context={
        'user_id': request.session.get('user_id'),
        'user_name': request.session.get('user_name'),
        'user_status_id': request.session.get('user_status_id')
        }
    )


# ==========================================
# 꿀팁 게시판 글 등록
# ==========================================
@router.post('/jobtip/write')
def jobtipWriteData(
    request: Request,
    job_tip_title: str = Form(),
    job_tip_detail: str = Form(),
    job_tip_attachment: list[UploadFile] = File(default=[]),
    session: Session = Depends(get_session)
):
    # 로그인 확인
    user_id = request.session.get('user_id')

    if not user_id:
        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )

    # 제목과 내용 확인
    if job_tip_title.strip() == '' or job_tip_detail.strip() == '':
        return RedirectResponse(
            url='/jobtip/write',
            status_code=303
        )

    # 이미지 파일 종류 확인
    for file in job_tip_attachment:
        if not file.filename:
            continue

        if file.content_type not in ALLOWED_IMAGES:
            return popup_error("지원하지 않는 이미지 형식입니다.")

    # 이미지 서버 저장
    attachment_paths = []

    for file in job_tip_attachment:
        if not file.filename:
            continue

        extension = ALLOWED_IMAGES[file.content_type]
        filename = f"{uuid4().hex}{extension}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        attachment_paths.append(
            f"/assets/uploads/{filename}"
        )

    attachment_value = json.dumps(
        attachment_paths,
        ensure_ascii=False
    )

    # 글 쓴 날짜
    job_tip_date = datetime.now()

    # 번호 생성
    sql_no = text('''
        SELECT MAX(job_tip_no)
        FROM job_tip
    ''')

    result = session.execute(sql_no).scalar()

    if result is None:
        job_tip_no = 1
    else:
        job_tip_no = result + 1

    # DB에 값 저장
    sql_insert = text('''
        INSERT INTO job_tip (
            job_tip_no,
            job_tip_title,
            job_tip_date,
            job_tip_detail,
            job_tip_attachment,
            user_id
        )
        VALUES (
            :job_tip_no,
            :job_tip_title,
            :job_tip_date,
            :job_tip_detail,
            :job_tip_attachment,
            :user_id
        )
    ''')

    session.execute(
        sql_insert,
        {
            'job_tip_no': job_tip_no,
            'job_tip_title': job_tip_title,
            'job_tip_date': job_tip_date,
            'job_tip_detail': job_tip_detail,
            'job_tip_attachment': attachment_value,
            'user_id': user_id
        }
    )

    session.commit()

    return RedirectResponse(
        url='/jobgogo/jobtip',
        status_code=303
    )


@router.get('/jobtip/6n23')
def ytb():
    print('easteregg')
    return RedirectResponse(
        url='https://www.youtube.com/watch?v=Zpx83AUavn0',
        status_code=302)

# 글 읽기
@router.get('/jobtip/{job_tip_no}')
def jobtip_read(
    request: Request,
    job_tip_no: str,
    session: Session = Depends(get_session)
):
    if not job_tip_no.isdecimal():
        return popup_error("게시글이 없습니다!")

    job_tip_no = int(job_tip_no)
    
    sql = text('''
        SELECT
            job_tip_no,
            job_tip_title,
            job_tip_detail,
            job_tip_date,
            job_tip_attachment,
            user_id
        FROM job_tip
        WHERE job_tip_no = :job_tip_no
    ''')

    job = session.execute(
        sql,
        {'job_tip_no': job_tip_no}
    ).mappings().first()

    if job is None:
        return popup_error("게시글이 없습니다....")

    # DB에 저장된 이미지 가져오기
    attachment_paths = json.loads(
        job['job_tip_attachment'] or '[]'
    )

    # 댓글 가져오기
    reple_sql = text('''
        SELECT
            reple_no,
            reple,
            parent_reple_no,
            job_tip_no,
            user_id
        FROM job_tip_comment
        WHERE job_tip_no = :job_tip_no
        ORDER BY reple_no DESC
    ''')
    reple_list = session.execute(
        reple_sql,
        {'job_tip_no': job_tip_no}
    ).mappings().fetchall()


    return templates.TemplateResponse(
        request=request,
        name='jobtip-read.html',
        context={
            'job': job,
            'attachment_paths': attachment_paths,

            'reple_list' : reple_list,

            'user_id': request.session.get('user_id'),
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )

# 댓글 달기
@router.post('/jobtip/{job_tip_no}')
def jobtip_comment_write(
    request: Request,
    job_tip_no: int,
    reple: str = Form(),
    session: Session = Depends(get_session)
):
    user_id = request.session.get('user_id')

    if not user_id:
        return popup_error("로그인이 필요합니다.")

    sql = text('''
        INSERT INTO job_tip_comment (
            reple,
            parent_reple_no,
            job_tip_no,
            user_id
        )
        VALUES (
            :reple,
            NULL,
            :job_tip_no,
            :user_id
        )
    ''')

    session.execute(
        sql,
        {
            'reple': reple,
            'job_tip_no': job_tip_no,
            'user_id': user_id
        }
    )

    session.commit()

    return RedirectResponse(
        url=f'/jobtip/{job_tip_no}',
        status_code=303
    )


# 댓글 삭제
@router.post('/jobtip/{job_tip_no}/reple/del')
def jobtip_comment_delete(
    request: Request,
    job_tip_no: int,
    reple_no: int = Form(),
    session: Session = Depends(get_session)
):
    user_id = request.session.get('user_id')

    if not user_id:
        return popup_error("로그인이 필요합니다.")

    sql = text('''
        DELETE FROM job_tip_comment
        WHERE reple_no = :reple_no
        AND job_tip_no = :job_tip_no
        AND user_id = :user_id
    ''')

    result = session.execute(
        sql,
        {
            'reple_no': reple_no,
            'job_tip_no': job_tip_no,
            'user_id': user_id
        }
    )

    if result.rowcount == 0:
        session.rollback()
        return popup_error("로그인이 필요합니다.")

    session.commit()

    return RedirectResponse(
        url=f'/jobtip/{job_tip_no}',
        status_code=303
    )




# 삭제버튼
@router.post('/jobtip/{job_tip_no}/delete')
def jobtip_delete(
    request: Request,
    job_tip_no: int,
    session: Session = Depends(get_session)
):
    # 로그인 확인
    user_id = request.session.get('user_id')

    if not user_id:
        return popup_error("로그인이 필요합니다.")

    # 게시글 존재 여부 및 작성자 확인
    sql_check = text('''
        SELECT user_id
        FROM job_tip
        WHERE job_tip_no = :job_tip_no
        FOR UPDATE
    ''')

    job = session.execute(
        sql_check,
        {'job_tip_no': job_tip_no}
    ).mappings().first()

    if job is None:
        session.rollback()
        return popup_error("게시글이 없습니다")

    # 본인이 작성한 게시글인지 확인
    if job['user_id'] != user_id:
        session.rollback()
        return popup_error("본인이 작성한 게시글만 지울 수 있습니다.")

    try:
        # 게시글에 연결된 댓글 전체 삭제
        sql_delete_reple = text('''
            DELETE FROM job_tip_comment
            WHERE job_tip_no = :job_tip_no
        ''')

        session.execute(
            sql_delete_reple,
            {'job_tip_no': job_tip_no}
        )

        # 게시글 삭제
        sql_delete_jobtip = text('''
            DELETE FROM job_tip
            WHERE job_tip_no = :job_tip_no
            AND user_id = :user_id
        ''')

        result = session.execute(
            sql_delete_jobtip,
            {
                'job_tip_no': job_tip_no,
                'user_id': user_id
            }
        )

        if result.rowcount == 0:
            session.rollback()
            return popup_error("삭제 실패.")

        # 댓글과 게시글 삭제를 DB에 확정
        session.commit()

    except Exception:
        session.rollback()
        raise

    # 4. 게시글 목록으로 이동
    return RedirectResponse(
        url='/jobgogo/jobtip',
        status_code=303
    )

