from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy import text, URL

from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import APIRouter

import os
from dotenv import load_dotenv

router = APIRouter()
templates = Jinja2Templates(directory='templates/')

load_dotenv()

database_url = os.getenv('DATABASE_URL')

router.mount(
    "/assets",
    StaticFiles(directory="assets"),
    name="assets"
)

engine = create_engine(database_url, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

@router.get('/admin')
def admin_dashboard(request:Request, session: Session = Depends(get_session)):
    print('/admin 실행')

    # #관리자가 아니면 경고 페이지로 쫓아냄 
    # if request.session.get('user_id') != 'admin':
    #     return RedirectResponse(
    #         url='/warning',
    #         status_code=303
    #     )

    # 현재 회원의 수가 몇 명인지 세는 SQL문 
    sql1 = text('''
        select count(*)
        from user
    ''')
    results1 = session.execute(sql1).mappings().fetchall()

    # API 호출 건수를 세는 SQL문 
    sql2=text('''
        select count(*)
        from api_sync_log
    ''')
    results2 = session.execute(sql2).mappings().fetchall()

    # 최근 게시물을 긁어오는 SQL문 (by Google Gemini)
    sql3=text('''
        select 
            '공지' as category,
            notice_title as title,
            user_id,
            notice_date as created_at 
        from notice
        union all 
        select 
            '취업 꿀팁' as category,
            job_tip_title as title,
            user_id, 
            job_tip_date as created_at
        from job_tip
        order by created_at desc
    ''')
    results3 = session.execute(sql3).mappings().fetchall() 

    return templates.TemplateResponse(request, 'admin-dashboard.html',{
        'total_users_count' : results1[0]['count(*)'],
        'total_api_call_count' : results2[0]['count(*)'],
        'recent_posts' : results3
    })

@router.get('/admin-users')
def users(request:Request, session: Session = Depends(get_session)):
    print('/admin-users 실행')

    # 등록된 모든 회원을 가져오는 SQL문
    sql1 = text('''
        select * from user
    ''')
    results1 = session.execute(sql1).mappings().fetchall()

    # 신고가 접수된 취업꿀팁 게시판의 글 제목과 신고 사유를 긁어오는 SQL문 
    sql2 = text('''
        select 
            rl.report_id , jt.user_id as author_id , us.user_name,  rl.user_id as reporter_id, jt.job_tip_title, rl.report_reason
        from 
            report_logs as rl
        left join 
            job_tip as jt on rl.job_tip_no = jt.job_tip_no
        left join 
            user as us on jt.user_id = us.user_id
    ''')
    results2 = session.execute(sql2).mappings().fetchall()

    # 신고 건수를 세는 SQL문 
    sql3 = text ('''
        select count(*)
        from report_logs
    ''')
    results3 = session.execute(sql3).mappings().fetchall()

    return templates.TemplateResponse(request, 'admin-users.html', {
        'users' : results1,
        'reports' : results2,
        'report_count' : results3[0]['count(*)']
    })

@router.post('/admin/user/report/delete/{report_id}')
def report_delete(request: Request, report_id : int, session : Session = Depends(get_session)):
    sql = text ('''
        delete from report_logs
        where report_id = :report_id
    ''')
    session.execute(sql, {'report_id' : report_id})

@router.post('/admin/user/warning/{user_id}')
def user_warning(request:Request, user_id: str, session: Session = Depends(get_session)):
    print('경고 횟수를 1 올립니다.')
    # 회원의 누적 경고 횟수를 1씩 올리는 SQL문
    sql1 = text('''
        update user
        set 
            warning_count = warning_count + 1
        where 
            user_id = :user_id
            AND user_status_id != 1
    ''')

    # 경고횟수가 5회 이상일경우, 상태 코드를 4 : 경고로 변경
    sql2 = text('''
        update user
        set 
            user_status_id = 4 
        where 
            warning_count >=5 and user_id = :user_id
            AND user_status_id != 1
    ''')

    # 경고횟수가 10회 이상일경우, 상태 코드를 5: 정지로 변경 
    sql3 = text('''
        update user
        set 
            user_status_id = 5 
        where
            warning_count >= 10 and user_id = :user_id 
            AND user_status_id != 1
    ''')
    session.execute(sql1, {'user_id' : user_id})
    session.execute(sql2, {'user_id' : user_id})
    session.execute(sql3, {'user_id' : user_id})
    session.commit()

    return RedirectResponse(url='/admin-users' , status_code=303)

@router.post('/admin/user/warning/delete/{user_id}')
def user_warning_delete(request:Request, user_id: str, session: Session = Depends(get_session)):
    print('경고 횟수를 1 낮춥니다')

    # 현재 경고 횟수를 먼저 확인합니다.
    sql_all = text('''
        select warning_count 
        from user 
        where user_id = :user_id
    ''')
    result = session.execute(sql_all, {'user_id' : user_id})
    warning_count = result.mappings().fetchone()
    print ('현재 경고 횟수 : ' , warning_count['warning_count'] )

    # 경고 횟수가 1 이상인경우에만 경고를 1개 줄여줍니다. (0개 미만으로 내려가지 않게 방어)
    sql = text('''
        update user
        set warning_count = warning_count - 1
        where user_id = :user_id and warning_count >= 1
    ''')
    session.execute(sql, {'user_id' : user_id})
    session.commit()

    return RedirectResponse(url='/admin-users' , status_code=303)

@router.post('/admin/user/suspension/{user_id}')
def user_suspension (request:Request, user_id: str, session: Session = Depends(get_session)):
    print('계정을 정지합니다.')

    sql = text('''
        update user 
        set user_status_id = 5
        where user_id = :user_id
            AND user_status_id != 1
    ''')
    session.execute(sql, {'user_id' : user_id})
    session.commit()

    return RedirectResponse(url='/admin-users', status_code=303)

@router.post('/admin/user/unsuspension/{user_id}')
def user_unsuspension(request:Request, user_id: str, session: Session = Depends(get_session)):
    print('계정 정지를 해제합니다.')

    sql = text('''
        update user
        set user_status_id = 3
        where user_id = :user_id
    ''')
    session.execute(sql, {'user_id' : user_id})
    session.commit()

    return RedirectResponse(url='/admin-users', status_code=303)

@router.post('/admin/user/delete/{user_id}')
def user_delete(request:Request, user_id: str, session:Session = Depends(get_session)):
    print('계정을 삭제합니다.')

    sql = text('''
        delete from user
        where user_id = :user_id
            AND user_status_id != 1
    ''')
    try:
        session.execute(sql, {'user_id' : user_id})
        session.commit()

        return RedirectResponse (url='/admin-users' , status_code=303)
    except  Exception as e:
        session.rollback()
        print(e)

        return RedirectResponse (
            url='/admin-users', status_code=303
        )

@router.get('/admin/user/search')
def search_user(request: Request, keyword : str = "" , session: Session = Depends(get_session)):
    print('사용자 검색을 실행합니다.')

    # 이름이나 아이디에 검색어가 포함된 회원을 찾는 SQL문
    sql_search = text('''
        select * from user
        where (
            :keyword = ''
            or user_name like :search_keyword
            or user_id like :search_keyword
        )
        order by user_id
    ''')
    result = session.execute(sql_search, {
        'keyword' : keyword,
        'search_keyword' : f'%{keyword}%'
})
    search_list = result.mappings().fetchall()

    sql_report = text('''
        select 
            rl.report_id , jt.user_id as author_id , us.user_name,  rl.user_id as reporter_id, jt.job_tip_title, rl.report_reason
        from 
            report_logs as rl
        left join 
            job_tip as jt on rl.job_tip_no = jt.job_tip_no
        left join 
            user as us on jt.user_id = us.user_id
    ''')
    post_report_list = (
        session.execute(sql_report).mappings().fetchall()
    )

    sql_count = text('''
        select count(*)
        from report_logs
    ''')
    report_count = (
        session.execute(sql_count).mappings().fetchall()
    )

    return templates.TemplateResponse (
        request, 'admin-users.html', {
            'users' : search_list,
            'reports' : post_report_list,
            'report_count' : report_count[0]['count(*)']
        }
    )

@router.get('/admin-board')
def admin_board(request:Request, session: Session = Depends(get_session)):
    print('게시물관리 페이지로 이동합니다.')

    sql_post = text('''
        select 
            '공지' as category,
            notice_title as title,
            notice_id as post_no,
            notice_detail as post_detail,
            user_id,
            notice_date as created_at 
            from notice
            union all 
        select 
            '취업 꿀팁' as category,
            job_tip_title as title,
            job_tip_no as post_no,
            job_tip_detail as post_detail,
            user_id, 
            job_tip_date as created_at
            from job_tip
    ''')
    result = session.execute(sql_post).mappings().fetchall()

    return templates.TemplateResponse (
        request, 'admin-board.html', {
            'posts' : result
        }
    )

@router.post('/admin/board/delete/{post_number}')
def delete_post(request: Request,  post_number : int, category: str = Form(...) , session: Session = Depends(get_session)):
    print('글 삭제를 실행합니다.')

    try:
            # 카테고리 값에 따라 대상 테이블과 PK 컬럼을 분기 
            if category in ['공지' , '공지사항']:
                sql = text('''
                    delete from notice
                    where notice_id = :post_number
                ''')
            else:
                sql = text('''
                    delete from job_tip
                    where job_tip_no = :post_number
                ''')
            session.execute(sql, {'post_number' : post_number})
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"게시글 삭제에 실패했습니다. : {e}")

    return RedirectResponse (
                url='/admin-board', status_code=303
            )

@router.get('/warning')
def warning_page(request:Request, session: Session = Depends(get_session)):
    print('경고 페이지로 이동합니다.')
    return templates.TemplateResponse(request, 'warning.html')

@router.get('/logout')
def logout(request: Request):
    print('로그아웃합니다.')
    request.session.clear()

    return RedirectResponse(
        url = '/jobgogo' ,
        status_code=303
    )