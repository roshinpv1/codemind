import os
import shutil
import uuid
import datetime
import subprocess
import sys
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from foundation.engine import ReasoningEngine
from llm.factory import get_llm_client
from policy.policy_engine import PolicyEngine
from api.models import IndexRequest
from indexing.git_utils import clone_repo
from cocoindex_app.flow import code_index_flow
from cocoindex_app.search import search, pool
from memory_service.storage_manager import StorageManager

router = APIRouter()
engine = ReasoningEngine(get_llm_client())
policy = PolicyEngine()
storage_manager = StorageManager()

class Req(BaseModel):
    tenant: str
    repo: str
    branch: str = "main"
    instruction: str
    context_query: str
    role: str = "senior_engineer"
    task: str = "explain_code"
    constraints: dict = {}

@router.post("/execute")
async def execute(r: Req):
    policy.check("user", r.instruction)
    return {"result": await engine.execute(
        r.tenant, r.repo, r.branch, r.instruction, r.context_query, r.constraints,
        role=r.role, task=r.task
    )}

@router.post("/search")
async def search_endpoint(payload: dict):
    query = payload.get("query")
    repo = payload.get("repo")
    branch = payload.get("branch")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    result = await search(query, repo=repo, branch=branch)
    return {"results": result.results}

@router.post("/setup")
def setup_environment():
    # 1. Database Setup
    with pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS indexing_status (
                    index_id UUID PRIMARY KEY,
                    repo_url TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    # 2. Filesystem Setup
    root = os.environ.get("CODEBASE_ROOT", "./data/repos")
    if not os.path.exists(root):
        os.makedirs(root, exist_ok=True)
    
    # 3. CocoIndex Setup
    venv_python = sys.executable
    try:
        subprocess.run(
            [venv_python, "-m", "cocoindex.cli", "setup", "-f", "cocoindex_app.flow"],
            check=True,
            capture_output=True,
            text=True
        )
        coco_status = "synced"
    except subprocess.CalledProcessError as e:
        coco_status = f"failed: {e.stderr}"
    
    # 4. MongoDB Setup
    if os.environ.get("STORAGE_BACKEND") == "faiss_mongo":
        try:
            from memory_service.mongo_store import MongoStore
            MongoStore()
            mongo_status = "connected"
        except Exception as e:
            mongo_status = f"failed: {str(e)}"
    else:
        mongo_status = "skipped"

    return {
        "status": "environment_setup_complete", 
        "details": {
            "pgvector": "enabled", 
            "codebase_root": root,
            "cocoindex": coco_status,
            "mongodb": mongo_status
        }
    }

async def run_indexing(index_id: str, repo_url: str, branch: str):
    try:
        meta = clone_repo(repo_url, branch)
        os.environ["CODEBASE_PATH"] = meta["path"]
        os.environ["REPO_NAME"] = meta["repo"]
        os.environ["BRANCH_NAME"] = meta["branch"]
        os.environ["INDEX_RUN_ID"] = meta["run_id"]

        await code_index_flow.update_async()

        if os.environ.get("STORAGE_BACKEND") == "faiss_mongo":
            from memory_service.faiss_store import FAISSStore
            import numpy as np
            output = await code_index_flow.query("get_all_embeddings").eval_async()
            faiss_store = FAISSStore()
            faiss_store.reset()
            embeddings = []
            metadata = []
            for item in output.results:
                embeddings.append(item["embedding"])
                meta_item = {k: v for k, v in item.items() if k != "embedding"}
                metadata.append(meta_item)
            if embeddings:
                faiss_store.add(np.array(embeddings).astype('float32'), metadata)
                faiss_store.save()

        storage_manager.update_status(index_id, "completed")
    except Exception as e:
        print(f"Indexing failed for {index_id}: {e}")
        storage_manager.update_status(index_id, "failed", error=str(e))

@router.post("/index")
async def index_repo(req: IndexRequest, background_tasks: BackgroundTasks):
    try:
        setup_environment()
        index_id = str(uuid.uuid4())
        storage_manager.create_status(index_id, req.repo_url, req.branch)
        background_tasks.add_task(run_indexing, index_id, req.repo_url, req.branch)
        return {
            "status": "indexing_started",
            "index_id": index_id,
            "message": "The codebase is being indexed in the background.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status/{index_id}")
async def get_index_status(index_id: str):
    status = storage_manager.get_status(index_id)
    if not status:
        raise HTTPException(status_code=404, detail="Index ID not found")
    if isinstance(status.get("created_at"), datetime.datetime):
        status["created_at"] = status["created_at"].isoformat()
    return {
        "index_id": index_id,
        "status": status["status"],
        "error": status.get("error"),
        "created_at": status.get("created_at"),
        "repo_url": status["repo_url"],
        "branch": status["branch"]
    }

@router.post("/reset")
def reset_all_data():
    with pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            tables = [r[0] for r in cur.fetchall()]
            if tables:
                tables_sql = ", ".join([f'"{t}"' for t in tables])
                cur.execute(f"TRUNCATE TABLE {tables_sql} CASCADE")
                conn.commit()
    storage_manager.reset_all()
    codebase_root = os.environ.get("CODEBASE_ROOT", "./data/repos")
    if os.path.exists(codebase_root):
        for item in os.listdir(codebase_root):
            item_path = os.path.join(codebase_root, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Failed to delete {item_path}. Reason: {e}")
    return {"status": "setup_reset_complete"}
