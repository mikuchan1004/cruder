from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session

from database import get_session
from DTO.UserDTO import User



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
# 마이 페이지 접속 라우팅
########################################################## 

@router.get('/jobgogo/mypage')
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

        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )

    # 조회한 회원 정보를 HTML에 전달
    return templates.TemplateResponse(
            request,
            'my-page.html',
            {
                'user': user
            }
        )

    # 옛날 방식
    # return templates.TemplateResponse(
    #     request=request,
    #     name='my-page.html',
    #     context={
    #         'user': user,
    #         'user_id': request.session.get('user_id'),
    #         'user_name': request.session.get('user_name'),
    #         # 'user_status_id': request.session.get('user_status_id')
    #     }
    # )


# @router.get('/jobgogo/mypage')
# def mypage(request: Request):

#     # 로그인 여부 체크(세션에서)
#     login_chk=request.session.get('member_id')

#     if not login_chk:
#         return RedirectResponse(
#                 url='/jobgogo',
#                 status_code=303
#             )

#     return templates.TemplateResponse(
#             request,
#             'my-page.html',
#             {
#                 'member_id': login_chk
#             }
#         )