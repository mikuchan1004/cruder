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

    # RAG 답변
    answer = ask_rag(question)

    # 하이브리드 검색
    results = hybrid(question)["hits"]["hits"]
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
