from fastapi import Request, Form
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, create_engine,text
from fastapi.responses import RedirectResponse
from database import get_session
# ai 질문 처리하기 위해서 불러옴
from router.api_router import ask_rag,hybrid
# gpt를 통한 임베딩
from router.GPT_embedding import ask_gpt, hybrid_gpt


from datetime import date
from fastapi import Depends
from sqlalchemy import text
from sqlmodel import Session
from database import get_session
router = APIRouter()
templates = Jinja2Templates(directory='templates/')

# 로그인 여부 체크 함수
from fastapi import HTTPException
def isLogin(request:Request):
    user_id=request.session.get['user_id']
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail='로그인이 필요합니다...'
        )
    return user_id    
    


@router.get("/jobgogo/chatjobpt")
def ai_chat(request:Request):
    
    return templates.TemplateResponse(
        request,'ai-chat.html'
    )
    
 #  ai 질문 처리하는 곳
 

# AI 질문 처리 및 GPT 채용 추천 결과 출력

@router.post("/api/chatjopt")
def chat_result(
    
    request: Request,
    # 사용자가 입력한거
    question: str = Form(...),
    session: Session = Depends(get_session)
    
    
):
    # 1. 로그인여부를  확인
    user_id = request.session.get("user_id")

    if not user_id:
         raise HTTPException(
             status_code=401,
             detail='로그인이 필요합니다...'
         )
    # 혹시 모를 공백제거
    question = question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="질문을 입력하세요."
        )
     # 질문 내용을 실제로 db에 저장하는 과정 추가
     

    sql=text('''
           insert into ai_chat_room(
            ai_chat_date,user_id)
            values (NOW(),:user_id)
                ''') 
    session.exec(sql,params={
        "user_id":user_id
    })
    # 생성도니 채팅방의 pk를 가져오기
    
    ai_chat_id=session.exec(
        text('''
             select LAST_INSERT_ID()
             ''')
    ).scalar_one()
    
    chat_msg_sql=text('''
                insert into ai_chat_message(
                    ai_chat_detail,ai_chat_id
                )
                values (
                    :ai_chat_detail,
                    :ai_chat_id) ''')
    session.exec(chat_msg_sql,params={
        'ai_chat_detail':question,
        'ai_chat_id':ai_chat_id
    })
    
    # 4. 사용자 질문 메시지 PK 가져오기
    ai_chat_message_id = session.exec(
     text("SELECT LAST_INSERT_ID()")
       ).scalar_one()
                 
   
        

    print("1. POST 요청 도착", flush=True)
    print("2. 사용자 질문:", question, flush=True)

    # 2. GPT RAG 실행
    print("3. GPT RAG 실행 시작", flush=True)

    gpt_result = ask_gpt(question)

    print("4. GPT RAG 실행 성공", flush=True)

    # 3. GPT 답변 추출
    answer = gpt_result["answer"]

    # 4. GPT 검색 결과
    results = gpt_result["jobs"]

    print("5. 검색된 공고:", len(results), flush=True)

    # 5. HTML에서 사용할 데이터 형식으로 변환
    jobs = []

    for job in results:

        jobs.append({
            "recrut_pblnt_sn": job.get("recrutPblntSn"),
            "inst_nm": job.get("instNm"),
            "recrut_pbanc_ttl": job.get("recrutPbancTtl"),
            "work_rgn_nm_lst": job.get("workRgnNmLst"),
            "recrut_se_nm": job.get("recrutSeNm"),
            "recrut_nope": job.get("recrutNope"),
            "pbanc_bgng_ymd": job.get("pbancBgngYmd"),
            "pbanc_end_ymd": job.get("pbancEndYmd"),
            "ongoing_yn": job.get("ongoingYn"),
            "src_url": job.get("srcUrl")
        })

    print("6. HTML 결과 전달", flush=True)

    # 6. 결과 페이지 출력
    return templates.TemplateResponse(
    request=request,
    name="ai-chat-result.html",
    context={
        "question": question,
        "answer": answer,
        "jobs": jobs,
        "bookmarked_job_ids": []
    }
)