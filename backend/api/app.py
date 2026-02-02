from dotenv import load_dotenv

# Load env vars before importing any other modules that might use them
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import cocoindex
from api.routes import router

cocoindex.init()

app = FastAPI(title="CodeMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo purposes. In prod, restrict to frontend URL.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
