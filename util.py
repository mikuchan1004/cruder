import os
import json

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from pathlib import Path
from config import ELASTIC_API_KEY,ELASTIC_ENDPOINT,GEMINI_API_KEY

from google import genai

# .env 파일 읽기
load_dotenv()

# .env에 저장된 값 가져오기
ELASTIC_ENDPOINT = os.getenv("ELASTIC_ENDPOINT")
# ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

# Elasticsearch 연결
es = Elasticsearch(
    ELASTIC_ENDPOINT
)
# 제미나이 연결
gemini=genai.Client(api_key=GEMINI_API_KEY)


# 디버깅용
# print(response)
print("===== INFERENCE 목록 =====")
# print(response)
print("==========================")


# print("현재 Python ELASTIC_ENDPOINT:")
# print(ELASTIC_ENDPOINT)

# print("ELASTIC_ENDPOINT =", repr(ELASTIC_ENDPOINT))
# print("ELASTIC_API_KEY 존재 여부 =", bool(ELASTIC_API_KEY))

def formatter(resp):
    results = []
    # 우리가 넣은 내용만 쏙 빼온다
    for hit in resp["hits"]["hits"]:
        document = hit.get("_source", {})

        results.append({
            'document': hit.get("_source", {}),
            'score': hit.get("_score")
        })

    return {
        "results": results, 
        "total": resp["hits"]["total"]["value"]
    }







def load_documents():
    BASE_DIR = Path(__file__).resolve().parents[0]
    DOCUMENT_FILE = BASE_DIR / 'data' / 'data.json'

    result = {}

    try:
        with open(DOCUMENT_FILE, 'r', encoding='utf-8') as file:
            result = json.load(file)
            print(result)

    except Exception as e:
        print('open 하다가 오류 발생 :', e)

    return result