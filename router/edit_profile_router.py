from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlmodel import Session

from database import get_session
from DTO.UserDTO import User
from DTO.UserStatusDTO import UserStatus
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


# 수정 페이지 접속 라우팅
@router.get('/jobgogo/mypage/edit')
def mypage(
    request: Request,
    session: Session = Depends(get_session)
):

    # 로그인한 회원 ID 가져오기
    login_chk = request.session.get('user_id')

    # 로그인하지 않은 경우
    if not login_chk:
        return RedirectResponse(
            url='/jobgogo',
            status_code=303
        )

    # 실제 로그인한 회원의 DB 정보 조회
    user = session.get(User, login_chk)

    # 회원 정보가 존재하지 않는 경우
    if user is None:
        request.session.clear()

        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )

    # 조회한 회원 정보를 HTML에 전달
    return templates.TemplateResponse(
        request=request,
        name='edit-profile.html',
        context={
            'user': user,
            'user_id': request.session.get('user_id'),
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )

ctx_pw = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# 수정 사항 저장
@router.post('/jobgogo/mypage/edit')
def update_profile(
    request: Request,
    user_name: str = Form(),
    user_pw: str = Form(default=''),
    user_pw_confirm: str = Form(default=''),
    user_nickname: str = Form(),
    user_home: str = Form(),
    user_email: str = Form(),
    user_phone: str = Form(),
    session: Session = Depends(get_session)
):
    # 현재 로그인한 회원
    login_user_id = request.session.get('user_id')

    if not login_user_id:
        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )

    # DB에서 회원 조회
    user = session.get(User, login_user_id)

    if user is None:
        request.session.clear()

        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )

    # 비밀번호를 입력했다면 확인값 검사
    if user_pw:
        if user_pw != user_pw_confirm:
            return templates.TemplateResponse(
                request=request,
                name='edit-profile.html',
                context={
                    'user': user,
                    'user_id': request.session.get('user_id'),
                    'user_name': request.session.get('user_name'),
                    'user_status_id': request.session.get('user_status_id'),
                    'error': '비밀번호가 일치하지 않습니다.'
                },
                status_code=400
            )

        # 새 비밀번호 암호화
        user.user_pw = ctx_pw.hash(user_pw)

    # 회원 정보 수정
    user.user_name = user_name
    user.user_nickname = user_nickname
    user.user_home = user_home
    user.user_email = user_email
    user.user_phone = user_phone

    session.add(user)
    session.commit()
    session.refresh(user)

    # 이름은 세션에도 저장돼 있으므로 같이 갱신
    request.session['user_name'] = user.user_name

    return RedirectResponse(
        url='/jobgogo/mypage',
        status_code=303
    )