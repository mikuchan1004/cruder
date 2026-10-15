from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy import text, URL

from fastapi import HTTPException
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import APIRouter

import os
from dotenv import load_dotenv

router = APIRouter()
templates = Jinja2Templates(directory='templates/')

load_dotenv()

database_url = os.getenv('DATABASE_URL')

engine = create_engine(database_url, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

def require_admin(request: Request):
    user_status_id = request.session.get('user_status_id')

    if user_status_id not in (1, 2):
        raise HTTPException(
            status_code=303,
            headers={
                'Location': '/jobgogo/warning'
            }
        )

def require_super_admin(request: Request):
    if request.session.get('user_status_id') != 1:
        raise HTTPException(
            status_code=303,
            headers={'Location': '/jobgogo/warning'}
        )

@router.get('/jobgogo/admin')
def admin_dashboard(
    request:Request, 
    session: Session = Depends(get_session), 
    # #관리자가 아니면 경고 페이지로 쫓아냄
    _: None = Depends(require_admin)
):
    print('/admin 실행')

    # 현재 회원의 수가 몇 명인지 세는 SQL문 
    sql1 = text('''
        select count(*)
        from user
    ''')
    results1 = session.execute(sql1).mappings().fetchall()

    # 모집중인 채용 공고가 몇 개인지 세는 SQL문 
    sql2=text('''
        select count(*)
        from jobs
        where ongoing_yn = 'Y'
    ''')
    results2 = session.execute(sql2).mappings().fetchall()

    # 최근 게시물을 긁어오는 SQL문 (by Google Gemini)
    sql3=text('''
        select 
            '공지' as category,
            notice_title as title,
            user_id,
            notice_date as created_at 
        from notice
        union all 
        select 
            '취업 꿀팁' as category,
            job_tip_title as title,
            user_id, 
            job_tip_date as created_at
        from job_tip
        order by created_at desc
        limit 5
    ''')
    results3 = session.execute(sql3).mappings().fetchall() 

    # 답변 대기 중인 문의가 몇 개인지 세는 SQL문
    sql4=text('''
        select count(*)
        from inquiry
        where inquiry_status_id = 1
    ''')
    results4 = session.execute(sql4).mappings().fetchall()

    return templates.TemplateResponse(request, 'admin-dashboard.html',{
        'total_users_count' : results1[0]['count(*)'],
        'total_ongoing_count' : results2[0]['count(*)'],
        'recent_posts' : results3,
        'inquiry_wating_count' : results4[0]['count(*)']
    })

@router.get('/jobgogo/admin-users')
def users(
    request:Request, 
    session: Session = Depends(get_session), 
    _: None = Depends(require_admin)
):
    print('/admin-users 실행')

    # 등록된 모든 회원을 가져오는 SQL문
    sql1 = text('''
        select * from user
    ''')
    results1 = session.execute(sql1).mappings().fetchall()

    # 신고가 접수된 취업꿀팁 게시판의 글 제목과 신고 사유를 긁어오는 SQL문 
    sql2 = text('''
        select 
            rl.report_id , jt.user_id as author_id , us.user_name,  rl.user_id as reporter_id, jt.job_tip_title, rl.report_reason
        from 
            report_logs as rl
        left join 
            job_tip as jt on rl.job_tip_no = jt.job_tip_no
        left join 
            user as us on jt.user_id = us.user_id
    ''')
    results2 = session.execute(sql2).mappings().fetchall()

    # 신고 건수를 세는 SQL문 
    sql3 = text ('''
        select count(*)
        from report_logs
    ''')
    results3 = session.execute(sql3).mappings().fetchall()

    return templates.TemplateResponse(request, 'admin-users.html', {
        'users' : results1,
        'reports' : results2,
        'report_count' : results3[0]['count(*)']
    })

# 신고 삭제
@router.post('/jobgogo/admin/user/report/delete/{report_id}')
def report_delete(
    request: Request, 
    report_id : int, 
    session : Session = Depends(get_session), 
    _: None = Depends(require_admin)
):
    sql = text ('''
        delete from report_logs
        where report_id = :report_id
    ''')
    session.execute(sql, {'report_id' : report_id})
    session.commit()

    return RedirectResponse(
        url='/jobgogo/admin-users',
        status_code=303
    )

@router.post('/jobgogo/admin/user/warning/{user_id}')
def user_warning(request:Request, user_id: str, session: Session = Depends(get_session), _: None = Depends(require_admin)):
    print('경고 횟수를 1 올립니다.')
    # 회원의 누적 경고 횟수를 1씩 올리는 SQL문
    sql1 = text('''
        update user
        set 
            warning_count = warning_count + 1
        where 
            user_id = :user_id
            AND user_status_id != 1
    ''')

    # 경고횟수가 5회 이상일경우, 상태 코드를 4 : 경고로 변경
    sql2 = text('''
        update user
        set 
            user_status_id = 4 
        where 
            warning_count >=5 and user_id = :user_id
            AND user_status_id != 1
    ''')

    # 경고횟수가 10회 이상일경우, 상태 코드를 5: 정지로 변경 
    sql3 = text('''
        update user
        set 
            user_status_id = 5 
        where
            warning_count >= 10 and user_id = :user_id 
            AND user_status_id != 1
    ''')
    session.execute(sql1, {'user_id' : user_id})
    session.execute(sql2, {'user_id' : user_id})
    session.execute(sql3, {'user_id' : user_id})
    session.commit()

    return RedirectResponse(url='/jobgogo/admin-users' , status_code=303)

@router.post('/jobgogo/admin/user/warning/delete/{user_id}')
def user_warning_delete(
    request: Request,
    user_id: str,
    session: Session = Depends(get_session),
    _: None = Depends(require_admin)
):
    print('경고 횟수를 1 낮춥니다.')

    # 경고 횟수가 1 이상일 때만 1 감소
    sql_warning = text('''
        update user
        set warning_count = warning_count - 1
        where user_id = :user_id
        and warning_count >= 1
    ''')

    session.execute(sql_warning, {'user_id': user_id})

    # 경고 횟수가 5 미만으로 내려갔다면
    # 경고 회원(4)을 일반 회원(3)으로 복구
    sql_status = text('''
        update user
        set user_status_id = 3
        where user_id = :user_id
        and warning_count < 5
        and user_status_id = 4
    ''')

    session.execute(sql_status, {'user_id': user_id})
    session.commit()

    return RedirectResponse(
        url='/jobgogo/admin-users',
        status_code=303
    )

@router.post('/jobgogo/admin/user/suspension/{user_id}')
def user_suspension (request:Request, user_id: str, session: Session = Depends(get_session), _: None = Depends(require_admin)):
    print('계정을 정지합니다.')

    sql = text('''
        update user 
        set user_status_id = 5
        where user_id = :user_id
            AND user_status_id != 1
    ''')
    session.execute(sql, {'user_id' : user_id})
    session.commit()

    return RedirectResponse(url='/jobgogo/admin-users', status_code=303)

@router.post('/jobgogo/admin/user/unsuspension/{user_id}')
def user_unsuspension(request:Request, user_id: str, session: Session = Depends(get_session), _: None = Depends(require_admin)):
    print('계정 정지를 해제합니다.')

    sql = text('''
        update user
        set user_status_id = 3
        where user_id = :user_id
        and user_status_id = 5
    ''')
    session.execute(sql, {'user_id' : user_id})
    session.commit()

    return RedirectResponse(url='/jobgogo/admin-users', status_code=303)

@router.post('/jobgogo/admin/user/delete/{user_id}')
def user_delete(request:Request, user_id: str, session:Session = Depends(get_session), _: None = Depends(require_admin)):
    print('계정을 삭제합니다.')

    sql = text('''
        delete from user
        where user_id = :user_id and user_status_id not in (1, 2)
    ''')
    try:
        session.execute(sql, {'user_id' : user_id})
        session.commit()

        return RedirectResponse (url='/jobgogo/admin-users' , status_code=303)
    except  Exception as e:
        session.rollback()
        print(e)

        return RedirectResponse (
            url='/jobgogo/admin-users', status_code=303
        )

@router.get('/jobgogo/admin/user/search')
def search_user(request: Request, keyword : str = "" , session: Session = Depends(get_session), _: None = Depends(require_admin)):
    print('사용자 검색을 실행합니다.')

    # 이름이나 아이디에 검색어가 포함된 회원을 찾는 SQL문
    sql_search = text('''
        select * from user
        where (
            :keyword = ''
            or user_name like :search_keyword
            or user_id like :search_keyword
        )
        order by user_id
    ''')
    result = session.execute(sql_search, {
        'keyword' : keyword,
        'search_keyword' : f'%{keyword}%'
})
    search_list = result.mappings().fetchall()

    sql_report = text('''
        select 
            rl.report_id , jt.user_id as author_id , us.user_name,  rl.user_id as reporter_id, jt.job_tip_title, rl.report_reason
        from 
            report_logs as rl
        left join 
            job_tip as jt on rl.job_tip_no = jt.job_tip_no
        left join 
            user as us on jt.user_id = us.user_id
    ''')
    post_report_list = (
        session.execute(sql_report).mappings().fetchall()
    )

    sql_count = text('''
        select count(*)
        from report_logs
    ''')
    report_count = (
        session.execute(sql_count).mappings().fetchall()
    )

    return templates.TemplateResponse (
        request, 'admin-users.html', {
            'users' : search_list,
            'reports' : post_report_list,
            'report_count' : report_count[0]['count(*)']
        }
    )

@router.post('/jobgogo/admin/user/get-admin/{user_id}')
def get_admin (
    request:Request,
    user_id: str,
    session:Session = Depends(get_session),
    _: None = Depends(require_super_admin)
):
    print('관리자 권한을 부여합니다.')

    sql = text('''
        update user
        set user_status_id = 2 
        where user_id = :user_id and user_status_id = 3
    ''')

    session.execute(sql, {'user_id' : user_id})
    session.commit()

    return RedirectResponse (
        url='/jobgogo/admin-users' , status_code=303
    )

@router.post('/jobgogo/admin/user/lose-admin/{user_id}')
def lose_admin (
    request:Request, 
    user_id: str, 
    session:Session = Depends(get_session), 
    _: None = Depends(require_super_admin)
):
    print('관리자 권한을 박탈합니다.')

    sql = text('''
        update user
        set user_status_id = 3
        where user_id = :user_id
        and user_status_id = 2
    ''')

    session.execute(sql, {'user_id' : user_id})
    session.commit()

    return RedirectResponse (
        url='/jobgogo/admin-users' , status_code=303
    )


@router.get('/jobgogo/admin-board')
def admin_board(request:Request, page:int = 1, session: Session = Depends(get_session), _: None = Depends(require_admin)):
    print('게시물관리 페이지로 이동합니다.')

    # 페이지 번호 계산 
    if page < 1:
        page=1
    
    # 한 페이지당 게시물 7개씩 보여줌
    limit = 10
    offset = (page - 1)* limit
    
    sql_post = text('''
        select 
            '공지' as category,
            notice_title as title,
            notice_id as post_no,
            notice_detail as post_detail,
            user_id,
            notice_date as created_at 
            from notice
            union all 
        select 
            '취업 꿀팁' as category,
            job_tip_title as title,
            job_tip_no as post_no,
            job_tip_detail as post_detail,
            user_id, 
            job_tip_date as created_at
            from job_tip
            limit :limit offset :offset
    ''')
    post_result = session.execute(sql_post, params={
         'limit' : limit,
        'offset' : offset
    }).mappings().fetchall()

    # DB에 저장된 게시물의 갯수를 세는 SQL문
    sql_count=text('''
        select (select count(*) from notice) + (select count(*) from job_tip) as total_count
    ''')
    result = session.execute(sql_count)
    total_count = result.fetchone()[0]

    # 총 페이지 계산 
    total_pages = (total_count + limit - 1) // limit

    # 몇 그룹씩 끊을지 생각하기 
    page_group = 5

    # 시작 페이지 그룹 계산하기 
    start_page = ((page - 1)//5)*page_group+1

    # 마지막 페이지 그룹 계산
    end_page = start_page+page_group-1

    if end_page>total_pages:
        end_page=total_pages

    return templates.TemplateResponse (
        request, 'admin-board.html', {
            'posts' : post_result,
            'page' : page,
            'total_pages' : total_pages,
            'start_page' : start_page,
            'end_page' : end_page
        }
    )

@router.post('/jobgogo/admin-board/delete/{post_number}')
def delete_post(
    request: Request, 
    post_number : int, 
    category: str = Form(...),
    session: Session = Depends(get_session), 
    _: None = Depends(require_admin)
):
    print('글 삭제를 실행합니다.')

    try:
        # 카테고리 값에 따라 대상 테이블과 PK 컬럼을 분기 
        if category in ['공지' , '공지사항']:
            sql = text('''
                delete from notice
                where notice_id = :post_number
            ''')
        else:
            sql = text('''
                delete from job_tip
                where job_tip_no = :post_number 
            ''')
        session.execute(sql, {'post_number' : post_number , 'category' : category})
        session.commit()

        return RedirectResponse (
            url='/jobgogo/admin-board', status_code=303
        )

    except Exception as e:
        session.rollback()
        print(f"게시글 삭제에 실패했습니다. : {e}")

    return RedirectResponse (
        url='/jobgogo/admin-board', status_code=303
    )

@router.get('/jobgogo/admin-recult')
def recult(request:Request, page:int = 1,  session:Session = Depends(get_session), _: None = Depends(require_admin)):
    print('채용 공고 관리 페이지로 이동합니다.')

    # 페이지 번호 계산 
    if page < 1:
        page=1

    # 한 페이지당 게시물 10개씩 보여줌
    limit = 10 
    offset = (page - 1)* limit

    # DB에 저장된 채용 공고들을 뽑아옵니다.
    sql_jobs = text('''
        select 
            recrut_pblnt_sn, 
            recrut_pbanc_ttl, 
            inst_nm, 
            pbanc_bgng_ymd, 
            pbanc_end_ymd, 
            recrut_se_nm,
            work_rgn_nm_lst
        from jobs         
        limit :limit offset :offset
    ''')

    results = session.execute(sql_jobs , params = {
        'limit' : limit,
        'offset' : offset
    }).mappings().fetchall()

    # DB에 저장된 채용 공고의 수를 세는 SQL문 
    sql_count = text('''
        select count(*) from jobs 
    ''')

    result = session.execute(sql_count)
    total_count = result.fetchone()[0]

    # 총 페이지 계산 
    total_pages = (total_count + limit - 1) // limit

    # 몇 그룹씩 끊을지 생각하기 
    page_group = 5

    # 시작 페이지 그룹 계산하기 
    start_page = ((page - 1)//5)*page_group+1

    # 마지막 페이지 그룹 계산
    end_page = start_page+page_group-1

    if end_page>total_pages:
        end_page=total_pages

    return templates.TemplateResponse(request, 'admin-recult.html' , {
        'recrut_lists' : results,
        'page' : page,
        'total_pages' : total_pages,
        'start_page' : start_page,
        'end_page' : end_page
    })

@router.post('/jobgogo/admin-recult/delete/{recrut_pblnt_sn}')
def delete_recult(
    request: Request,  
    recrut_pblnt_sn : int, 
    session: Session = Depends(get_session), 
    _: None = Depends(require_admin)
):
    print('채용공고를 삭제합니다.')

    # DB에 저장되어있는 채용공고를 삭제하는 SQL문 
    sql = text('''
        delete from jobs
        where recrut_pblnt_sn = :recrut_pblnt_sn
    ''')

    session.execute(sql , {'recrut_pblnt_sn' : recrut_pblnt_sn })
    session.commit()

    return RedirectResponse(
        url='/jobgogo/admin-recult' ,
        status_code=303
    )

@router.get('/jobgogo/admin-inquiry')
def admin_inquiry(request:Request,  session:Session = Depends(get_session)):
    print('문의관리 페이지로 이동합니다.')

    # 1:1 문의를 DB에서 긁어오는 SQL문 
    sql = text('''
        select 
            inq.inquiry_id, 
            u.user_name, 
            inq.inquiry_type, 
            inq.inquiry_title,
            inq.inquiry_status_id,
            inq.inquiry_answer,
            inqs.inquiry_status_name
        from inquiry as inq
        left join user as u on inq.user_id = u.user_id
        left join inquiry_status as inqs on inq.inquiry_status_id = inqs.inquiry_status_id
    ''')

    results = session.execute(sql).mappings().fetchall()

    return templates.TemplateResponse(request,'admin-inquiry.html', {
        'inquiry_lists' : results
    })

@router.post('/jobgogo/admin-inquiry/answer/{id}')
def answer_inquiry(  request: Request,  
    id : int, inquiry_answer: str = Form(),
    session: Session = Depends(get_session), 
    _: None = Depends(require_admin)):
    print ('문의 답변을 실행합니다.')

    sql = text ('''
        update inquiry 
        set 
            inquiry_answer = :inquiry_answer,
            inquiry_status_id = 2,
            inquiry_answer_date = NOW()
        where inquiry_id = :id
    ''')
    session.execute(sql, {
        'id' : id,
        'inquiry_answer' : inquiry_answer
    }) 
    session.commit()

    return RedirectResponse(url='/jobgogo/admin-inquiry' , status_code=303)

@router.post('/jobgogo/admin-inquiry/delete/{id}')
def delete_inquiry(  request: Request,  
    id : int, session: Session = Depends(get_session), 
    _: None = Depends(require_admin)):
    print ('문의 삭제를 실행합니다.')

    sql=text('''
    delete from inquiry 
    where inquiry_id = :id
    ''')

    session.execute(sql, {'id' : id})
    session.commit()
    return RedirectResponse(url='/jobgogo/admin-inquiry' , status_code=303)


@router.get('/jobgogo/warning')
def warning_page(
    request:Request, 
    session: Session = Depends(get_session)
):
    print('경고 페이지로 이동합니다.')
    return templates.TemplateResponse(request, 'warning.html')

@router.get('/jobgogo/logout')
def logout(request: Request):
    print('로그아웃합니다.')
    request.session.clear()

    return RedirectResponse(
        url = '/jobgogo' ,
        status_code=303
    )