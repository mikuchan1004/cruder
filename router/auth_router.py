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
from passlib.context import CryptContext
from sqlmodel import Session, select,text

from database import get_session
from DTO.UserDTO import User


router = APIRouter()
templates = Jinja2Templates(directory='templates/')



# =========================================================
# 회원가입 
# =========================================================

@router.get('/jobgogo/signup')
def _signup(request: Request):
    
    messege=request.session.pop('idChk_Messge',None)
    
    return templates.TemplateResponse(
        request=request,
        name='signup.html',
        context={
            'messege':messege
        }
    )
    
# =========================================================
# 회원가입 처리(여기서 null값 못들어가게 막겠습니다.)
# =========================================================
ctx_pw = CryptContext(
    schemes=['argon2'],
    deprecated='auto'
)

def crypt(txt):
    return ctx_pw.hash(txt)

@router.post('/api/signup')
def signup(
    user:User=Form(),
    session: Session = Depends(get_session)):
    
    print('api/signup 실행 성공함')
    print('user',user)
    
    hashed=crypt(user.user_pw)
    

    #  회원가입할떄 user_status_id를 일반 유저를 1로 일단 넘기기
    try:
        sql=text('''
               insert into user(
                user_id,
                user_name,
                user_pw,
                user_nickname,
                user_home,
                user_email,
                user_phone,
                user_status_id
                 )  
              VALUES(
                  :user_id,
                  :user_name,
                  :user_pw,
                  :user_nickname,
                  :user_home,
                  :user_email,
                  :user_phone,
                  3
                            
              )    
                 
                 ''')
        session.exec(
            sql,
            params={
                'user_id': user.user_id,
                'user_name': user.user_name,
                'user_pw': hashed,
                'user_nickname':user.user_nickname,
                'user_home':user.user_home,
                'user_email':user.user_email,
                'user_phone':user.user_phone
            }
        )
  
    
    except Exception as e:
        print(e,'에러에러에러에러')
        
    return RedirectResponse(
        url='/jobgogo/login',
        status_code=303
        )


##########################################################
# 로그인 페이지 접속 라우팅
########################################################## 

# 로그인 창 접속
@router.get('/jobgogo/login')
def jobgogo(
    request: Request
):
    login_error = request.session.pop('login_error', None)

    return templates.TemplateResponse(
        request,
        'login.html',
        {
            'login_error': login_error
        }
    )
    

# =========================================================
# 로그인 처리
# =========================================================

def verify(orig, hashed):
    return ctx_pw.verify(orig, hashed)


@router.post("/jobgogo/login")
def login(
    request: Request,
    user_id: str=Form(),
    user_pw: str=Form(),
    session: Session = Depends(get_session)
):
    print('가는거니')
    
       
    sql=text('''
             select *
             from user
             where user_id=:user_id
             
             ''')
    
    result=session.exec(
               sql,
               params={
                   'user_id':user_id,
                   
               }
           )
    
    user=result.mappings().fetchone()

    # 아이디 검증
    if user is None:
        request.session['login_error']='아이디 또는 비밀번호가 올바르지 않습니다.'
        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )
    
    #  비밀번호가 틀렸을 경우  
    if not verify(user_pw,user['user_pw']):
        request.session['login_error']='아이디 또는 비밀번호가 올바르지 않습니다.'
        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )
    
    # 정지 회원 로그인 차단
    if user['user_status_id'] == 5:
        # request.session.clear()
        request.session['login_error'] = '정지된 계정입니다.'
        return RedirectResponse(
            url='/jobgogo/login',
            status_code=303
        )
        
      
    # 로그인 성공!
    
    request.session.pop('login_error',None)
            
    request.session["user_id"] = user['user_id']
    request.session["user_name"] = user['user_name']
    request.session["user_status_id"] = user['user_status_id']
    request.session["user_nickname"] = user['user_nickname']
    request.session["user_phone"] = user['user_phone']
    request.session["user_home"] = user['user_home']
    request.session["user_email"] = user['user_email']
    request.session["warning_count"] = user['warning_count']

    
    
    return RedirectResponse(
           url='/jobgogo',
           status_code=303
       )

# id 중복 확인 

@router.get('/api/check-id')
def chkId(
    request: Request,
    user_id:str,
    session: Session = Depends(get_session)
     ):
    
    
    sql=text('''
          select user_id
          from user
          where user_id=:user_id   
             ''')
    
    
    result=session.exec(
                   sql,
                   params={
                       'user_id':user_id,
                       
                   }
               ) 
    user=result.mappings().fetchone()
    #세선에 저장하자아
    if user is not None:
        request.session['idChk_Messge']='이미 존재하는 아이디 입니다'
    else:
        request.session['idChk_Messge']='사용 가능한 아이디 입니다'
    
    return RedirectResponse(
           url='/jobgogo/signup',
           status_code=303
       )

    
    
    # # 아이디로 사용자 조회
    # statement = select(User).where(User.user_id == user_id)
    # user = session.exec(statement).first()

    # 아이디가 존재하지 않음
    # if user is None:
    #     return templates.TemplateResponse(
    #         request=request,
    #         name="login.html",
    #         context={
    #             "error": "아이디 또는 비밀번호가 올바르지 않습니다.",
    #             "entered_user_id": user_id
    #         },
    #         status_code=401
    #     )

    # # 비밀번호 불일치
    # if user.user_pw != user_pw:
    #     return templates.TemplateResponse(
    #         request=request,
    #         name="login.html",
    #         context={
    #             "error": "아이디 또는 비밀번호가 올바르지 않습니다.",
    #             "entered_user_id": user_id
    #         },
    #         status_code=401
    #     )

    # # 로그인 성공
    # request.session["user_id"] = user.user_id
    # request.session["user_name"] = user.user_name
    # request.session["user_status_id"] = user.user_status_id

    # return RedirectResponse(
    #     url="/jobgogo",
    #     status_code=303
    # )

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
    

    
