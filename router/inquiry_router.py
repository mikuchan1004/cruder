from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlmodel import Session, create_engine,text

from database import get_session


router = APIRouter()
templates = Jinja2Templates(directory='templates/')


################################################################################
#  1:1 문의 라우팅(로그인 된 사람만 접속 가능한 설정임.)
################################################################################

@router.get('/inquiry')
def inquiry(request:Request):
    print('1대일 문의 게시판 접속 성공함')
    # 로그인 안한 사람이 일대일 문의 게시판 접속 못하게 막는 코드
    login_chk=request.session.get('user_id')
    
    if not login_chk:
        return RedirectResponse(
                url='/jobgogo',
                status_code=303
            )
        
        
    return templates.TemplateResponse(
        request,'inquiry.html'
    )
    
    
    