
from foundation.context import ContextEngine
from foundation.constraints import ConstraintEngine

class ReasoningEngine:
    def __init__(self, llm):
        self.ctx = ContextEngine()
        self.cons = ConstraintEngine()
        self.llm = llm

    def execute(self, tenant, repo, branch, instruction, query, constraints):
        ctx = self.ctx.resolve(tenant, repo, branch, query)
        
        system_instruction = (
            "You are CodeMind, an autonomous software engineering assistant.\n\n"
            "Your role is to understand and reason about real-world codebases using "
            "indexed source code and semantic search results provided to you.\n\n"
            "Guidelines:\n"
            "- Base all answers strictly on the provided code context snippets.\n"
            "- Always cite the filename and relevance score when referring to specific code.\n"
            "- Do not invent files, APIs, or behavior not present in the code.\n"
            "- If context is insufficient, say so explicitly.\n"
            "- Follow existing code patterns, conventions, and libraries discovered in the context.\n"
            "- Explain trade-offs when multiple solutions exist.\n"
            "- Treat all code and data as confidential.\n\n"
            "Communication:\n"
            "- Use the same language as the user.\n"
            "- Be concise, precise, and technically accurate.\n"
        )
        
        constraint_str = ""
        if constraints.get("json"):
            constraint_str = "\n\nCRITICAL: Output MUST be valid JSON only."
        
        prompt = (
            f"SYSTEM:\n{system_instruction}\n"
            f"CONTEXT SNIPPETS (Retrieved Code):\n{ctx}\n"
            "--- END OF CONTEXT ---\n\n"
            f"USER INSTRUCTION: {instruction}"
            f"{constraint_str}"
        )
        
        
        print("\n" + "="*20 + " PROMPT BEGIN " + "="*20)
        print(prompt)
        print("="*20 + " PROMPT END " + "="*20 + "\n")
        
        out = self.llm.generate(prompt)
        return self.cons.enforce(out, constraints)
