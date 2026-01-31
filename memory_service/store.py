
from cocoindex_app.search import search

class CocoIndexStore:
    def search(self, tenant, repo, branch, query):
        return search(query, repo=repo, branch=branch)
