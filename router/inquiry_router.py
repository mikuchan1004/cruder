from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlmodel import Session, create_engine,text

from database import get_session
from DTO.InquiryDTO import Inquiry

from fastapi import Form

router = APIRouter()
templates = Jinja2Templates(directory='templates/')


################################################################################
#  1:1 문의 라우팅(로그인 된 사람만 접속 가능한 설정임.)
################################################################################

@router.get('/inquiry')
def inquiry(request:Request):
    print('1대일 문의 게시판 접속 성공함')
    # 로그인 안한 사람이 일대일 문의 게시판 접속 못하게 막는 코드
    user_id = request.session.get('user_id')
    print('id 체크',user_id)


    if user_id is None:
            return RedirectResponse(
                url='/jobgogo',
                status_code=303
            )

    return templates.TemplateResponse(
        request,'inquiry.html',

        context={
            'user_id': user_id,
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )

################################################################################
#  1:1 문의 등록하는 곳입니다
################################################################################
@router.post('/api/inquiry/add')
def inquiry_add(request:Request,
    inquiry_type:str=Form(),
    inquiry_title:str=Form(),
    inquiry_detail:str=Form(),
    session:Session=Depends(get_session)):
    
    user_id =request.session.get('user_id')
    
    try:  
        sql=text('''
            INSERT INTO inquiry(
            inquiry_title,
            inquiry_detail,
            inquiry_date,
            user_id,
            inquiry_status_id,
            inquiry_type
        )
        VALUES(
            :inquiry_title,
            :inquiry_detail,
            NOW(),
            :user_id,
            1,
            :inquiry_type
        )

        ''')
        result=session.exec(sql,
            params={
                'inquiry_type':inquiry_type,
                'inquiry_title':inquiry_title,
                'inquiry_detail':inquiry_detail,
                'user_id':user_id
            }
        )
        session.commit()
        
        return RedirectResponse(
            url='/inquiry',
            status_code=303
        )
       
    except Exception as e:
                print('에러',e)   


# 내가 쓴 글 목록 보는거
 
@router.get('/jobgogo/mypage/inquiry_list')
def inquiry_list(request:Request,
    session: Session = Depends(get_session)       
     ):
    user_id=request.session.get('user_id')
    
    if user_id is None:
        return RedirectResponse(
            url='/jobgogo'
            ,status_code=303
        )
    
    sql=text('''
             select *
             from inquiry
             where user_id=:user_id 
             
             ''')
    
    result=session.exec(
        sql,
        params={
          'user_id': user_id
        }
    )
    results= result.mappings().fetchall()
    
    # html 출력
    
    return templates.TemplateResponse(
    request=request,
    name='inquiry_result.html',
    context={
        'inquiries': results,
        'user_id': user_id,
        'user_name': request.session.get('user_name'),
        'user_status_id': request.session.get('user_status_id')
    }
)
    
    
# 문의 내역상세조회...!
@router.get('/jobgogo/inquiry/{inquiry_id}')
def inquiry_list_deatil(request:Request,
    inquiry_id:int,                                        
    session: Session = Depends(get_session)):
    
    user_id=request.session.get('user_id')
    print('id 체크',user_id)
    print('id 체크',inquiry_id)


    if user_id is None:
            return RedirectResponse(
                url='/jobgogo',
                status_code=303
            )
            
    sql=text('''
       select *
       from inquiry
       where inquiry_id=:inquiry_id
       and user_id=:user_id      
            ''')
    
    result=session.exec(
            sql,
            params={
               'user_id':user_id,
               'inquiry_id': inquiry_id
            }
        )  
    results= result.mappings().fetchone()
    
    # html 출력    
    return templates.TemplateResponse(
        request=request,
        name='inquiry_result_deatil.html',
        
        context={
            'inquiry':results,
            'user_id': user_id,
            'user_name': request.session.get('user_name'),
            'user_status_id': request.session.get('user_status_id')
        }
    )
    


       
    