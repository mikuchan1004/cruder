from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router.jobs_router import router as jobs_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://127.0.0.1:5500'
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(jobs_router)

@app.get('/')
def home():
    return "welcome!"

if __name__ == "__main__" :
    import uvicorn
    uvicorn.run('api:app', port=8000, reload=True, host='0.0.0.0')
    