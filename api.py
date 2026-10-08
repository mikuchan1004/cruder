from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router.main_router import router as main_router
from router.jobs_router import router as jobs_router


router = FastAPI()
router.include_router(main_router)
router.include_router(jobs_router)
router.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://127.0.0.1:5500'
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)



@router.get('/')
def home():
    return "welcome!"

if __name__ == "__main__" :
    import uvicorn
    uvicorn.run('api:router', port=8000, reload=True, host='0.0.0.0')
     