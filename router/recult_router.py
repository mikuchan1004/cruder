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
    session: Session = Depends(get_session)
):
    print('채용 공고 페이지 접속 성공!')   

    return templates.TemplateResponse(
        request=request,
        name='recult.html',
        context={

            # 로그인 세션
            "user_id": request.session.get("user_id"),
            "user_name": request.session.get("user_name"),
            "user_status_id": request.session.get("user_status_id")
        }
    )