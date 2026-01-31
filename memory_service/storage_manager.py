import os
from .mongo_store import MongoStore
from cocoindex_app.search import pool

class StorageManager:
    def __init__(self):
        self.backend = os.environ.get("STORAGE_BACKEND", "postgres")
        self.mongo = MongoStore() if self.backend == "faiss_mongo" else None

    def create_status(self, index_id: str, repo_url: str, branch: str):
        if self.backend == "faiss_mongo":
            self.mongo.create_status(index_id, repo_url, branch)
        else:
            with pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO indexing_status (index_id, repo_url, branch, status) VALUES (%s, %s, %s, %s)",
                        (index_id, repo_url, branch, "started")
                    )
                    conn.commit()

    def update_status(self, index_id: str, status: str, error: str = None):
        if self.backend == "faiss_mongo":
            self.mongo.update_status(index_id, status, error)
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
        if self.backend == "faiss_mongo":
            status = self.mongo.get_status(index_id)
            if status:
                status["_id"] = str(status["_id"])
            return status
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

    def reset_all(self):
        if self.backend == "faiss_mongo":
            self.mongo.reset()
        # Postgres reset logic is handled separately in routes.py for now
        # but could be moved here.
