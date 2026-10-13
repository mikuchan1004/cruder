from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, create_engine,text

from database import get_session


router = APIRouter()
templates = Jinja2Templates(directory='templates/')

@router.get('/chatjobpt')
def ai_chat(request:Request):
    
    return templates.TemplateResponse(
        request,'ai-chat.html'
    )