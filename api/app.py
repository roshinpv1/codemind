from fastapi import FastAPI
from dotenv import load_dotenv
import cocoindex
from api.routes import router

load_dotenv()
cocoindex.init()

app = FastAPI(title="CodeMind API")
app.include_router(router)
