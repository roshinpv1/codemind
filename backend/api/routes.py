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
storage_manager = StorageManager()
engine = ReasoningEngine(get_llm_client(), storage_manager=storage_manager)
policy = PolicyEngine()

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
    # 1. Database Setup (Only if postgres is active)
    backend = os.environ.get("STORAGE_BACKEND", "postgres")
    meta_store = os.environ.get("METADATA_STORE", "sqlite" if backend == "lancedb" else "postgres")
    
    if meta_store == "postgres":
        try:
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
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            namespace TEXT DEFAULT 'default'
                        )
                    """)
                    # Migration: Add namespace column if not exists
                    try:
                        cur.execute("ALTER TABLE indexing_status ADD COLUMN namespace TEXT DEFAULT 'default'")
                    except Exception:
                        # Column likely exists, ignore error
                        conn.rollback()
                    else:
                        conn.commit()
        except Exception as e:
            print(f"Postgres setup failed (ignoring as it might not be the active backend): {e}")
    
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
            "backend": backend,
            "meta_store": meta_store,
            "codebase_root": root,
            "cocoindex": coco_status,
            "mongodb": mongo_status
        }
    }

async def run_indexing(index_id: str, repo_url: str, branch: str):
    try:
        storage_manager.update_status(index_id, "cloning")
        meta = clone_repo(repo_url, branch)
        
        # --- Update Symlink for Flow ---
        # The flow monitors ./data/index_proxy. We point this link to the new repo.
        proxy_path = os.path.abspath(os.path.join(os.getcwd(), "data", "index_proxy"))
        target_repo_path = os.path.abspath(meta["path"])
        
        if os.path.exists(proxy_path) or os.path.islink(proxy_path):
            if os.path.isdir(proxy_path) and not os.path.islink(proxy_path):
                 shutil.rmtree(proxy_path)
            else:
                 os.unlink(proxy_path)
                 
        os.symlink(target_repo_path, proxy_path)
        # -------------------------------

        os.environ["CODEBASE_PATH"] = target_repo_path
        os.environ["REPO_NAME"] = meta["repo"]
        os.environ["BRANCH_NAME"] = meta["branch"]
        os.environ["INDEX_RUN_ID"] = meta["run_id"]

        storage_manager.update_status(index_id, "analyzing_ast")
        await code_index_flow.update_async()

        if os.environ.get("STORAGE_BACKEND") == "faiss_mongo":
            storage_manager.update_status(index_id, "vectorizing")
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
        storage_manager.create_status(index_id, req.repo_url, req.branch, req.namespace)
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

from fastapi.responses import JSONResponse

@router.get("/metrics")
async def get_metrics():
    try:
        try:
            # Get metadata counts from storage manager (sqlite/mongo/postgres)
            counts = storage_manager.get_counts()
        except Exception as e:
            print(f"Error getting counts: {e}")
            # Return empty counts to prevent UI crash
            counts = {"indexed_repos": 0, "success_runs": 0}
        
        # Total Embeddings (Best effort from Postgres)
        total_embeddings = 0
        try:
            with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM code_embeddings")
                    res = cur.fetchone()
                    if res:
                        total_embeddings = res[0]
        except Exception:
            # Ignore if table doesn't exist or other error
            pass
                
        return {
            "indexed_assets": counts["indexed_repos"],
            "reasoning_calls": 0, # Placeholder until we have a logs table
            "semantic_depth": "384-dim",
            "uptime": "99.9%",
            "total_embeddings": total_embeddings,
            "success_rate": f"{(counts['success_runs'] / (counts['success_runs'] + 1) * 100):.1f}%" if counts['success_runs'] > 0 else "100%"
        }
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": str(e), "trace": traceback.format_exc()})

@router.get("/activity")
async def get_activity(limit: int = 50):
    return storage_manager.get_activity(limit)

@router.get("/live")
async def get_live_pipelines():
    return storage_manager.get_live_pipelines()

@router.get("/repos")
async def get_indexed_repos():
    return storage_manager.get_indexed_repos()

@router.get("/executions")
async def get_executions(repo: str = None, limit: int = 50):
    """Retrieve execution logs from the active storage backend."""
    return storage_manager.get_executions(repo, limit)

@router.post("/reset")
def reset_all_data():
    backend = os.environ.get("STORAGE_BACKEND", "postgres")
    meta_store = os.environ.get("METADATA_STORE", "sqlite" if backend == "lancedb" else "postgres")
    
    if meta_store == "postgres" or backend == "postgres":
        try:
            with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                    tables = [r[0] for r in cur.fetchall()]
                    if tables:
                        tables_sql = ", ".join([f'"{t}"' for t in tables])
                        cur.execute(f"TRUNCATE TABLE {tables_sql} CASCADE")
                        conn.commit()
        except Exception:
            pass
            
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
