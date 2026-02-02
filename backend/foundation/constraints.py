
import json

class ConstraintEngine:
    def enforce(self, output, constraints):
        if constraints.get("json"):
            json.loads(output)
        if constraints.get("diff_only") and not output.startswith("---"):
            raise ValueError("diff_only violated")
        return output
