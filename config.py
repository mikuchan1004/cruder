import os
from dotenv import load_dotenv

load_dotenv()

ELASTIC_ENDPOINT = os.getenv('ELASTIC_ENDPOINT')
ELASTIC_API_KEY = os.getenv('ELASTIC_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ALIO_API_KEY = os.getenv('ALIO_API_KEY')