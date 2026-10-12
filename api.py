from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from router.main_router import router as main_router
from router.jobs_router import router as jobs_router
from router.login_router import router as login_router
# from router.signup_router import router as signup_router
# from router.mypage_router import router as mypage_router

from config import SESSION_SECRET_KEY

router = FastAPI()

router.include_router(main_router)
router.include_router(jobs_router)
router.include_router(login_router)
# router.include_router(signup_router)
# router.include_router(mypage_router)

router.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    same_site="lax",
    https_only=False
)

router.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://127.0.0.1:5500'
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# 정적 파일
router.mount(
    "/assets",
    StaticFiles(directory="assets"),
    name="assets"
)

@router.get('/')
def home():
    return "welcome!"

if __name__ == "__main__" :
    import uvicorn
    uvicorn.run('api:router', port=8000, reload=True, host='0.0.0.0')
     