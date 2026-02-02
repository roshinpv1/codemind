import os
from datetime import datetime
from .mongo_store import MongoStore
from .sqlite_store import SqliteStore
from cocoindex_app.search import pool

class StorageManager:
    def __init__(self):
        self.backend = os.environ.get("STORAGE_BACKEND", "postgres") # For vectors
        
        # Determine metadata store
        # If explicitly set, use it.
        # If storage_backend is 'lancedb', default metadata to 'sqlite' (fully local)
        # If storage_backend is 'faiss_mongo', default metadata to 'mongo'
        # Else default to 'postgres'
        
        default_meta = "postgres"
        if self.backend == "lancedb":
            default_meta = "sqlite"
        elif self.backend == "faiss_mongo":
            default_meta = "mongo"
            
        self.meta_type = os.environ.get("METADATA_STORE", default_meta)
        
        self.mongo = MongoStore() if self.meta_type == "mongo" else None
        self.sqlite = SqliteStore() if self.meta_type == "sqlite" else None

    def create_status(self, index_id: str, repo_url: str, branch: str, namespace: str = "default"):
        if self.meta_type == "mongo":
            self.mongo.create_status(index_id, repo_url, branch)
        elif self.meta_type == "sqlite":
            self.sqlite.create_status(index_id, repo_url, branch, namespace)
        else:
            with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO indexing_status (index_id, repo_url, branch, status, namespace) VALUES (%s, %s, %s, %s, %s)",
                        (index_id, repo_url, branch, "started", namespace)
                    )
                    conn.commit()

    def update_status(self, index_id: str, status: str, error: str = None):
        if self.meta_type == "mongo":
            self.mongo.update_status(index_id, status, error)
        elif self.meta_type == "sqlite":
            self.sqlite.update_status(index_id, status, error)
        else:
            with pool().connection() as conn:
                with conn.cursor() as cur:
                    if error:
                        cur.execute(
                            "UPDATE indexing_status SET status = %s, error = %s WHERE index_id = %s",
                            (status, error, index_id)
                        )
                    else:
                        cur.execute(
                            "UPDATE indexing_status SET status = %s WHERE index_id = %s",
                            (status, index_id)
                        )
                    conn.commit()

    def get_status(self, index_id: str):
        if self.meta_type == "mongo":
            status = self.mongo.get_status(index_id)
            if status:
                status["_id"] = str(status["_id"])
            return status
        elif self.meta_type == "sqlite":
            return self.sqlite.get_status(index_id)
        else:
            with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT status, error, created_at, repo_url, branch FROM indexing_status WHERE index_id = %s",
                        (index_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        return {
                            "status": row[0],
                            "error": row[1],
                            "created_at": row[2],
                            "repo_url": row[3],
                            "branch": row[4]
                        }
            return None

    def get_activity(self, limit: int = 50):
        if self.meta_type == "sqlite":
            return self.sqlite.get_activity(limit)
        
        if self.meta_type == "postgres":
             with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT repo_url, branch, status, created_at, index_id, error
                        FROM indexing_status 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (limit,))
                    rows = cur.fetchall()
                    activity = []
                    for r in rows:
                        activity.append({
                            "repo": r[0],
                            "repo_url": r[0],
                            "branch": r[1],
                            "status": r[2],
                            "date": r[3].isoformat() if isinstance(r[3], datetime) else str(r[3]),
                            "index_id": str(r[4]),
                            "error": r[5]
                        })
                    return activity
        return []

    def get_live_pipelines(self):
        if self.meta_type == "sqlite":
             return self.sqlite.get_live_pipelines()
        
        if self.meta_type == "postgres":
             with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT index_id, repo_url, branch, status, created_at 
                        FROM indexing_status 
                        WHERE status = 'started' OR status = 'pending'
                        ORDER BY created_at DESC
                    """)
                    rows = cur.fetchall()
                    live = []
                    for r in rows:
                        live.append({
                            "index_id": str(r[0]),
                            "repo_url": r[1],
                            "repo": r[1].split("/")[-1].replace(".git", ""),
                            "branch": r[2],
                            "status": r[3],
                            "started_at": r[4].isoformat() if isinstance(r[4], datetime) else str(r[4])
                        })
                    return live
        return []

    def get_indexed_repos(self):
        if self.meta_type == "sqlite":
            return self.sqlite.get_indexed_repos()
        
        if self.meta_type == "postgres":
             with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT ON (repo_url, branch) repo_url, branch, status, created_at
                        FROM indexing_status
                        ORDER BY repo_url, branch, created_at DESC
                    """)
                    rows = cur.fetchall()
                    repos = []
                    for r in rows:
                        if r[2] == 'completed':
                            repos.append({
                                "url": r[0],
                                "branch": r[1],
                                "name": r[0].split("/")[-1].replace(".git", ""),
                                "status": r[2],
                                "last_updated": r[3].isoformat() if r[3] else None
                            })
                    return repos
        return []

    def get_counts(self):
        if self.meta_type == "sqlite":
            return self.sqlite.get_counts()
        
        if self.meta_type == "postgres":
             with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(DISTINCT repo_url) FROM indexing_status WHERE status = 'completed'")
                    res_indexed = cur.fetchone()
                    indexed = res_indexed[0] if res_indexed else 0
                    
                    cur.execute("SELECT COUNT(*) FROM indexing_status WHERE status = 'completed'")
                    res_runs = res_runs = cur.fetchone()
                    runs = res_runs[0] if res_runs else 0
                    return {"indexed_repos": indexed, "success_runs": runs}
        return {"indexed_repos": 0, "success_runs": 0}

    def log_execution(self, execution_id: str, tenant: str, repo: str, instruction: str, response: str):
        if self.meta_type == "sqlite":
            self.sqlite.log_execution(execution_id, tenant, repo, instruction, response)
        elif self.meta_type == "mongo":
            pass # TODO: Implement mongo logging
        else:
            pass # TODO: Implement postgres logging

    def get_executions(self, repo: str = None, limit: int = 50):
        if self.meta_type == "sqlite":
            return self.sqlite.get_executions(repo, limit)
        elif self.meta_type == "mongo":
            return [] # TODO
        else:
            return [] # TODO

    def reset_all(self):
        if self.meta_type == "mongo":
            self.mongo.reset()
        elif self.meta_type == "sqlite":
            self.sqlite.reset()
        # Postgres reset logic is handled separately in routes.py for now
        # but could be moved here.
