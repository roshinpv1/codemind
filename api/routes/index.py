# api/routes/index.py
from fastapi import APIRouter
from api.models import IndexRequest
from indexing.git_utils import clone_repo
import os
import cocoindex
from cocoindex_app.main import code_index_flow

router = APIRouter()

@router.post("/index")
def index_repo(req: IndexRequest):
    meta = clone_repo(req.git_url, req.branch)

    # Inject runtime metadata
    os.environ["CODEBASE_PATH"] = meta["path"]
    os.environ["REPO_NAME"] = meta["repo"]
    os.environ["BRANCH_NAME"] = meta["branch"]
    os.environ["INDEX_RUN_ID"] = meta["run_id"]

    stats = code_index_flow.update()

    return {
        "status": "indexed",
        "repo": meta["repo"],
        "branch": meta["branch"],
        "run_id": meta["run_id"],
        "stats": stats,
    }
