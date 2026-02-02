
class PolicyEngine:
    def check(self, role, instruction):
        if role == "viewer" and "modify" in instruction.lower():
            raise PermissionError("Not allowed")
