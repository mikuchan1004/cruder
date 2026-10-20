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

router = APIRouter()
templates = Jinja2Templates(directory='templates/')

@router.get("/jobgogo/chatjobpt")
def ai_chat(request:Request):
    
    return templates.TemplateResponse(
        request,'ai-chat.html'
    )
    
 #  ai 질문 처리하는 곳
 
@router.post("/api/chatjopt")
def chat_result(request: Request, question: str = Form(...)):
    print("1. POST 요청 도착", flush=True)
    print("2. 사용자 질문:", question, flush=True)

    print("3. ask_rag 실행 시작", flush=True)

    # RAG 답변
    answer = ask_rag(question)
    print("4. ask_rag 실행 성공", flush=True)

    # 하이브리드 검색
    print("5. hybrid 실행 시작", flush=True)
    results = hybrid(question)["hits"]["hits"]
    print("6. hybrid 실행 성공", len(results), flush=True)
    # 결과 담는 곳입니다아...
    jobs = []

    for result in results:
        job = result["_source"]

        jobs.append({
            "recrut_pblnt_sn": job.get("recrutPblntSn"),
            "inst_nm": job.get("instNm"),
            "recrut_pbanc_ttl": job.get("recrutPbancTtl"),
            "recrut_se_nm": job.get("recrutSeNm"),
            "recrut_nope": job.get("recrutNope"),
            "pbanc_bgng_ymd": job.get("pbancBgngYmd"),
            "pbanc_end_ymd": job.get("pbancEndYmd"),
            "ongoing_yn": job.get("ongoingYn"),
            # 원문공고 url임.
            "src_url": job.get("srcUrl")
        })

    return templates.TemplateResponse(
        request,
        "ai-chat-result.html",
        {
            "answer": answer,
            "jobs": jobs,
            "bookmarked_job_ids": []
        }
    )

# @router.get('/api/chatjopt')
