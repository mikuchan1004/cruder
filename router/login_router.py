# from fastapi import Request, Form
# from fastapi import APIRouter
# from fastapi.templating import Jinja2Templates
# from fastapi import FastAPI, Depends
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import RedirectResponse

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlmodel import Session, select

from database import get_session
from DTO.UserDTO import User


router = APIRouter()
templates = Jinja2Templates(directory='templates/')



##########################################################
# 로그인 페이지 접속 라우팅
########################################################## 

# 로그인 창 접속
@router.get('/jobgogo/login')
def jobgogo(
    request: Request
):
    return templates.TemplateResponse(
        request,
        'login.html'
    )

# =========================================================
# 로그인 처리
# =========================================================

@router.post("/jobgogo/login")
def login(
    request: Request,
    user_id: Annotated[str, Form()],
    user_pw: Annotated[str, Form()],
    session: Session = Depends(get_session)
):
    # 아이디로 사용자 조회
    statement = select(User).where(User.user_id == user_id)
    user = session.exec(statement).first()

    # 아이디가 존재하지 않음
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "아이디 또는 비밀번호가 올바르지 않습니다.",
                "entered_user_id": user_id
            },
            status_code=401
        )

    # 비밀번호 불일치
    if user.user_pw != user_pw:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "아이디 또는 비밀번호가 올바르지 않습니다.",
                "entered_user_id": user_id
            },
            status_code=401
        )

    # 로그인 성공
    request.session["user_id"] = user.user_id
    request.session["user_name"] = user.user_name
    request.session["user_status_id"] = user.user_status_id

    return RedirectResponse(
        url="/jobgogo",
        status_code=303
    )

# =========================================================
# 로그아웃
# =========================================================

@router.get("/logout")
def logout(request: Request):
    request.session.clear()

    return RedirectResponse(
        url="/jobgogo",
        status_code=303
    )