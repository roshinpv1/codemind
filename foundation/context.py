from memory_service.service import MemoryService


class ContextEngine:
    def __init__(self):
        self.mem = MemoryService()

    def resolve(self, tenant, repo, branch, query):
        results = self.mem.get_context(tenant, repo, branch, query)

        blocks = []
        for r in results.results:
            block = (
                f"[{r['filename']}:{r['start']}-{r['end']}]\n"
                f"{r['code']}"
            )
            blocks.append(block)

        return "\n\n".join(blocks)
