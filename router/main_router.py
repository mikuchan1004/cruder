from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles




router = APIRouter()
templates = Jinja2Templates(directory='templates/')


# =========================================================
# static 폴더 연결
# =========================================================

router.mount(
    "/assets",
    StaticFiles(directory="assets"),
    name="assets"
)



##########################################################
# 메인 페이지 접속 라우팅
########################################################## 

@router.get('/jobgogo')
def jobgogo(
    request: Request
):
    return templates.TemplateResponse(
        request,
        'main.html'
    )
    
    