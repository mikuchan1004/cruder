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