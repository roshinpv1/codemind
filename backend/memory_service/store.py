
from cocoindex_app.search import search

class CocoIndexStore:
    async def search(self, tenant, repo, branch, query):
        return await search(query, repo=repo, branch=branch)
