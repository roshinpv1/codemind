import os
from pymongo import MongoClient
from datetime import datetime
import uuid

class MongoStore:
    def __init__(self):
        self.uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/codemind")
        self.client = MongoClient(self.uri)
        self.db = self.client.get_database()
        self.status_col = self.db.indexing_status

    def create_status(self, index_id: str, repo_url: str, branch: str):
        self.status_col.insert_one({
            "index_id": index_id,
            "repo_url": repo_url,
            "branch": branch,
            "status": "started",
            "error": None,
            "created_at": datetime.utcnow()
        })

    def update_status(self, index_id: str, status: str, error: str = None):
        update_data = {"status": status}
        if error:
            update_data["error"] = error
        self.status_col.update_one({"index_id": index_id}, {"$set": update_data})

    def get_status(self, index_id: str):
        return self.status_col.find_one({"index_id": index_id})

    def reset(self):
        # Drop all collections in the database
        for col in self.db.list_collection_names():
            self.db.drop_collection(col)
