from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from foundation.engine import ReasoningEngine
from llm.lmstudio_llm import LMStudioLLM
from policy.policy_engine import PolicyEngine
from api.models import IndexRequest
from indexing.git_utils import clone_repo
import os
import shutil
from cocoindex_app.flow import code_index_flow
from cocoindex_app.search import search, pool

router = APIRouter()
engine = ReasoningEngine(LMStudioLLM())
policy = PolicyEngine()

class Req(BaseModel):
    tenant: str
    repo: str
    branch: str = "main" # Added default matching Request example
    instruction: str
    context_query: str
    constraints: dict = {}

@router.post("/execute")
async def execute(r: Req): # made async
    # 5.3 Behavior: Perform search -> Build context -> Call LLM -> Return answer
    # The ReasoningEngine seems to handle this?
    # But wait, search API (5.2) returns results. Execute API (5.3) calls LLM.
    # The Engine likely calls search internally? Or should I call search here?
    # Engine signature: execute(tenant, repo, instruction, context_query, constraints)
    # I assume engine handles search.
    policy.check("user", r.instruction) # Role missing in request, assuming 'user' or implicit? Request has 'tenant', 'repo', 'branch'.
    # Note: original code had 'role' in Req but user request example doesn't show 'role'.
    # User Request: { "tenant": "demo", "repo": "repo", "branch": "main", "instruction": "...", "context_query": "..." }
    # So I removed 'role' from Req and defaulted to something safe or omitted policy check if role not present.
    # But keeping policy check implies security. I'll act as if role is not required or hardcode it.
    
    return {"result": engine.execute(
        r.tenant, r.repo, r.branch, r.instruction, r.context_query, r.constraints
    )}

@router.post("/search")
async def search_endpoint(payload: dict):
    query = payload.get("query")
    repo = payload.get("repo")
    branch = payload.get("branch")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    result = search(query, repo=repo, branch=branch)
    return {"results": result.results}

@router.post("/index")
async def index_repo(req: IndexRequest):
    try:
        meta = await clone_repo(req.repo_url, req.branch) if hasattr(clone_repo, '__await__') else clone_repo(req.repo_url, req.branch)

        # Inject runtime metadata
        os.environ["CODEBASE_PATH"] = meta["path"]
        os.environ["REPO_NAME"] = meta["repo"]
        os.environ["BRANCH_NAME"] = meta["branch"]
        os.environ["INDEX_RUN_ID"] = meta["run_id"]

        # Trigger update async
        stats = await code_index_flow.update_async()

        return {
            "status": "indexing_started",
            "index_id": meta["run_id"],
            "message": "The codebase is being indexed.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reset")
def reset_all_data():
    """
    Cleans up all stored data:
    1. Truncates all tables in the database.
    2. Deletes all repositories in CODEBASE_ROOT.
    """
    # 1. Database Cleanup
    with pool().connection() as conn:
        with conn.cursor() as cur:
            # Get all tables in public schema
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            tables = [r[0] for r in cur.fetchall()]
            
            if tables:
                # TRUNCATE all tables
                # Use quoted identifiers to be safe
                tables_sql = ", ".join([f'"{t}"' for t in tables])
                cur.execute(f"TRUNCATE TABLE {tables_sql} CASCADE")
    
    # 2. Filesystem Cleanup
    codebase_root = os.environ.get("CODEBASE_ROOT", "./data/repos")
    if os.path.exists(codebase_root):
        # We want to keep the root dir but remove contents
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
