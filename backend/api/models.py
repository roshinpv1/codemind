from pydantic import BaseModel

class IndexRequest(BaseModel):
    namespace: str = "default"
    repo_url: str
    branch: str = "main"
