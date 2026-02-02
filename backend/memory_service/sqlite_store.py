import sqlite3
import os
from datetime import datetime
import json

class SqliteStore:
    def __init__(self):
        self.db_path = os.environ.get("SQLITE_DB_PATH", "codemind.db")
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indexing_status (
                index_id TEXT PRIMARY KEY,
                namespace TEXT DEFAULT 'default',
                repo_url TEXT,
                branch TEXT,
                status TEXT,
                error TEXT,
                created_at TIMESTAMP
            )
        """)
        
        # Simple migration for existing DBs
        try:
            cursor.execute("ALTER TABLE indexing_status ADD COLUMN namespace TEXT DEFAULT 'default'")
        except sqlite3.OperationalError:
            pass
            
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                execution_id TEXT PRIMARY KEY,
                tenant TEXT,
                repo TEXT,
                instruction TEXT,
                response TEXT,
                created_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def create_status(self, index_id: str, repo_url: str, branch: str, namespace: str = "default"):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO indexing_status (index_id, repo_url, branch, status, created_at, namespace) VALUES (?, ?, ?, ?, ?, ?)",
            (index_id, repo_url, branch, "started", datetime.utcnow(), namespace)
        )
        conn.commit()
        conn.close()

    def update_status(self, index_id: str, status: str, error: str = None):
        conn = self._get_conn()
        cursor = conn.cursor()
        if error:
            cursor.execute(
                "UPDATE indexing_status SET status = ?, error = ? WHERE index_id = ?",
                (status, error, index_id)
            )
        else:
            cursor.execute(
                "UPDATE indexing_status SET status = ? WHERE index_id = ?",
                (status, index_id)
            )
        conn.commit()
        conn.close()

    def get_status(self, index_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM indexing_status WHERE index_id = ?", (index_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Convert row to dict to match Mongo behavior
            return dict(row)
        return None

    def log_execution(self, execution_id: str, tenant: str, repo: str, instruction: str, response: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO executions (execution_id, tenant, repo, instruction, response, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (execution_id, tenant, repo, instruction, response, datetime.utcnow())
        )
        conn.commit()
        conn.close()

    def get_executions(self, repo: str = None, limit: int = 50):
        # ... existing ...
        conn = self._get_conn()
        cursor = conn.cursor()
        if repo:
            cursor.execute("SELECT * FROM executions WHERE repo = ? ORDER BY created_at DESC LIMIT ?", (repo, limit))
        else:
            cursor.execute("SELECT * FROM executions ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_activity(self, limit: int = 50):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT namespace, repo_url, branch, status, created_at, index_id, error
            FROM indexing_status 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        activity = []
        for row in rows:
            r = dict(row)
            created_at = r["created_at"]
            if isinstance(created_at, datetime):
                date_str = created_at.isoformat()
            else:
                date_str = str(created_at)
                
            activity.append({
                "repo": r["repo_url"],
                "repo_url": r["repo_url"],
                "branch": r["branch"],
                "status": r["status"],
                "date": date_str,
                "index_id": r["index_id"],
                "error": r["error"],
                "namespace": r["namespace"]
            })
        return activity

    def get_live_pipelines(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT index_id, repo_url, branch, status, created_at, namespace 
            FROM indexing_status 
            WHERE status = 'started' OR status = 'pending'
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_indexed_repos(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        # Emulate DISTINCT ON logic using groupwise max
        cursor.execute("""
            SELECT t1.repo_url, t1.branch, t1.namespace, t1.status, t1.created_at
            FROM indexing_status t1
            WHERE t1.created_at = (
                SELECT MAX(t2.created_at) 
                FROM indexing_status t2 
                WHERE t2.repo_url = t1.repo_url AND t2.branch = t1.branch AND t2.namespace = t1.namespace
            )
            ORDER BY t1.namespace, t1.repo_url, t1.branch
        """)
        rows = cursor.fetchall()
        conn.close()
        repos = []
        for row in rows:
            r = dict(row)
            url = r["repo_url"]
            name = url.split("/")[-1].replace(".git", "") if url else "unknown"
            
            repos.append({
                "name": name,
                "url": url,
                "branch": r["branch"],
                "status": r["status"],
                "last_updated": str(r["created_at"]) if r["created_at"] else None
            })
        return repos

    def get_counts(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT repo_url) FROM indexing_status WHERE status = 'completed'")
        res_indexed = cursor.fetchone()
        indexed = res_indexed[0] if res_indexed else 0
        
        cursor.execute("SELECT COUNT(*) FROM indexing_status WHERE status = 'completed'")
        res_runs = cursor.fetchone()
        runs = res_runs[0] if res_runs else 0
        
        conn.close()
        return {"indexed_repos": indexed, "success_runs": runs}

    def reset(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self._init_db()
