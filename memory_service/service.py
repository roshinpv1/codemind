
from memory_service.store import CocoIndexStore

class MemoryService:
    def __init__(self):
        self.store = CocoIndexStore()

    async def get_context(self, tenant, repo, branch, query):
        return await self.store.search(tenant, repo, branch, query)
