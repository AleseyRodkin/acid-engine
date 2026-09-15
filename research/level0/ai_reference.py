"""Reference view for AI (level 0)."""
from __future__ import annotations

from typing import Any

from acid_engine.level2.identity import ContractId


class AIReferenceView:
    """
    Holds a locator for an atom (ContractId) and can gather context.
    Later it will talk to ContractRegistry.
    """
    def __init__(self, contract_id: ContractId, registry: Any | None = None):
        self.contract_id = contract_id
        self.registry = registry

    def describe(self) -> dict[str, Any]:
        """Return a structured description of the atom."""
        desc = {
            "contract_id": str(self.contract_id),
            "inputs": {},
            "outputs": {},
            "constraints": {},
            "history": [],
        }
        # If a registry is present, real data can be added
        if self.registry:
            try:
                module = self.registry.resolve(self.contract_id)
                desc["inputs"] = {"type": module.input_type}
                desc["outputs"] = {"type": module.output_type}
                desc["constraints"] = module.specification.policy.to_canonical_dict()
            except Exception:
                pass
        return desc