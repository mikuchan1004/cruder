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

    # 공지사항을 한눈에 볼 수 있게 가져오는 SQL문
    sql3=text('''
        select *
        from notice
        order by notice_date desc
    ''')
    results3 = session.execute(sql3).mappings().fetchall() 

    return templates.TemplateResponse(request, 'admin-dashboard.html',{
        'total_users_count' : results1[0]['count(*)'],
        'total_api_call_count' : results2[0]['count(*)'],
        'notices' : results3
    })

@router.get('/admin-users')
def users(request:Request, session: Session = Depends(get_session)):
    print('/admin-users 실행')

    # 등록된 모든 회원을 가져오는 SQL문
    sql1 = text('''
        select * from user
    ''')
    results1 = session.execute(sql1).mappings().fetchall()
    return templates.TemplateResponse(request, 'admin-users.html', {
        'users' : results1
    })

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
    ''')

    # 경고횟수가 5회 이상일경우, 상태 코드를 4 : 경고로 변경
    sql2 = text('''
        update user
        set 
            user_status_id = 4 
        where 
            warning_count >=5 and user_id = :user_id
    ''')

    # 경고횟수가 10회 이상일경우, 상태 코드를 5: 정지로 변경 
    sql3 = text('''
        update user
        set 
            user_status_id = 5 
        where
            warning_count >= 10 and user_id = :user_id 
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
    ''')
    try:
        session.execute({'user_id' : user_id})
        session.commit()

        return RedirectResponse (url='/admin/user?delete_result=success' , status_code=303)
    except  Exception as e:
        session.rollback()
        print(e)

        return RedirectResponse (
            url='/admin/user?delete_result=failed', status_code=303
        )