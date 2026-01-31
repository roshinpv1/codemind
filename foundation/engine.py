from foundation.context import ContextEngine
from foundation.constraints import ConstraintEngine
from foundation.prompts import CODEMIND_PROMPT_TEMPLATE
import json

class ReasoningEngine:
    def __init__(self, llm):
        self.ctx = ContextEngine()
        self.cons = ConstraintEngine()
        self.llm = llm

    async def execute(self, tenant, repo, branch, instruction, query, constraints, role="senior_engineer", task="explain_code"):
        # 1. Fetch Context
        ctx_text = await self.ctx.resolve(tenant, repo, branch, query)
        
        # 2. Assemble System Prompt from Template
        t = CODEMIND_PROMPT_TEMPLATE
        
        # Identity and Mission
        system_blocks = [
            f"{t['system']['identity']}\n{t['system']['mission']}",
            "\nCore Rules:",
            "\n".join([f"- {rule}" for rule in t['system']['core_rules']])
        ]
        
        # Context Handling
        system_blocks.append("\nContext Handling Rules:")
        system_blocks.extend([f"- {rule}" for rule in t['context_handling']['usage_rules']])
        
        # Role Overlay
        role_desc = t['role_overlays'].get(role, t['role_overlays']['senior_engineer'])
        system_blocks.append(f"\nCurrent Role: {role_desc}")
        
        # Task Prompt
        task_cfg = t['task_prompts'].get(task, t['task_prompts']['explain_code'])
        system_blocks.append(f"\nTask Instructions ({task}):")
        system_blocks.extend([f"- {instr}" for instr in task_cfg['instructions']])
        
        # Response Contract
        system_blocks.append("\nResponse Format Requirements:")
        for section in t['response_contract']['format']:
            system_blocks.append(f"- {section['section']}: {section['description']}")
            
        # Safety
        system_blocks.append("\nHard Constraints:")
        system_blocks.extend([f"- {c}" for c in t['safety']['hard_constraints']])
        
        system_prompt = "\n".join(system_blocks)
        
        # 3. Handle Constraints (JSON, etc.)
        constraint_str = ""
        if constraints.get("json"):
            constraint_str = "\n\nCRITICAL: Output MUST be valid JSON only. Follow the response contract within the JSON structure."
        
        # 4. Final Prompt Assembly
        prompt = (
            "=== SYSTEM ===\n"
            f"{system_prompt}\n\n"
            "=== CONTEXT SNIPPETS (Retrieved from CocoIndex) ===\n"
            f"{ctx_text}\n"
            "--- END OF CONTEXT ---\n\n"
            "=== USER INSTRUCTION ===\n"
            f"{instruction}\n"
            f"{constraint_str}"
        )
        
        # Debug Logging
        print("\n" + "="*20 + " PROMPT BEGIN " + "="*20)
        print(prompt)
        print("="*20 + " PROMPT END " + "="*20 + "\n")
        
        # 5. Generate and Enforce
        out = await self.llm.generate(prompt)
        return self.cons.enforce(out, constraints)
