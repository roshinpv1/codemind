
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
            "You are a helpful AI coding assistant. "
            "Use the provided code context to answer the user's instruction. "
            "If the context does not contain relevant information, state that you cannot answer based on the code provided.\n\n"
        )
        
        constraint_str = ""
        if constraints.get("json"):
            constraint_str = "\nOutput Format: JSON"
        
        prompt = (
            f"{system_instruction}"
            f"### Context:\n{ctx}\n\n"
            f"### Instruction:\n{instruction}"
            f"{constraint_str}"
        )
        
        out = self.llm.generate(prompt)
        return self.cons.enforce(out, constraints)
