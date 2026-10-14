from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, create_engine,text

from database import get_session


router = APIRouter()
templates = Jinja2Templates(directory='templates/')


################################################################################
#  1:1 문의 라우팅
################################################################################

@router.get('/inquiry')
def inquiry(request:Request):
    return templates.TemplateResponse(
        request,'inquiry.html'
    )