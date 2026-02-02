from memory_service.service import MemoryService


class ContextEngine:
    def __init__(self):
        self.mem = MemoryService()

    async def resolve(self, tenant, repo, branch, query):
        results = await self.mem.get_context(tenant, repo, branch, query)

        blocks = []
        for r in results.results:
            symbols_str = ", ".join(r['symbols']) if r.get('symbols') else "None"
            block = (
                f"--- File: {r['filename']} (Relevance Score: {r['score']:.4f}) ---\n"
                f"Symbols: {symbols_str}\n"
                f"Lines: {r['start']} to {r['end']}\n"
                f"{r['code']}\n"
            )
            blocks.append(block)

        return "\n\n".join(blocks)
